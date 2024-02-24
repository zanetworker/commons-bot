import json
import logging
import os
import re
import sys
import datetime, uuid
from pathlib import Path
import nest_asyncio

from dotenv import load_dotenv
from flask import Flask, request, jsonify

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient, WebhookClient
from index import IndexManager
from loaders import QdrantClientManager, EnvironmentConfig, YouTubeLoader
from query_engine import QueryEngineManager, QueryEngineToolsManager


from llama_index.agent import ReActAgent
from llama_index.llms import OpenAI


import graphsignal

graphsignal.configure(api_key=os.environ['GRAPH_SIGNAL_API_KEY'], deployment='commons-bot')

# Load environment variables from .env file or Lambda environment
load_dotenv()
nest_asyncio.apply()

# even noisier debugging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))



def format_links_for_slack(text):
    # Regex pattern to identify URLs
    url_pattern = r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)'
    formatted_text = re.sub(url_pattern, r'<\1|Link>', text)  # Replace URLs with Slack formatted links
    return formatted_text

def convert_markdown_links_to_slack(text):
    # Find all Markdown links in the text
    markdown_links = re.findall(r'\[([^\]]+)\]\((http[s]?://[^)]+)\)', text)

    # Replace each Markdown link with Slack's link format
    for link_text, url in markdown_links:
        slack_link = f"<{url}|{link_text}>"
        markdown_link = f"[{link_text}]({url})"
        text = text.replace(markdown_link, slack_link)

    return text


config = EnvironmentConfig()
qdrant_manager = QdrantClientManager(config)
qdrant_client = qdrant_manager.client

# Assuming 'client' is your initialized Qdrant client and 'youtube_transcripts' is your data
llm = OpenAI(model="gpt-4", temperature=0.0, stop_symbols=["\n"])

index_manager = IndexManager(qdrant_client, llm=llm)
youtube_loader = YouTubeLoader()
index = index_manager.create_or_load_index(youtube_transcripts=youtube_loader.yttranscripts)

query_engine_manager = QueryEngineManager(index)
agentContext = query_engine_manager.get_agent_context()
query_engine_transcripts = query_engine_manager.create_query_engine()

query_engine_tools_manager = QueryEngineToolsManager(query_engine_transcripts)
query_engine_tools = query_engine_tools_manager.query_engine_tools

# Initializes your app with your bot token and signing secret
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

# Flask app to handle requests
flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)

channel_list = slack_app.client.conversations_list().data
channel = next((channel for channel in channel_list.get('channels') if channel.get("name") == "test-bot"), None)
channel_id = channel.get('id')
slack_app.client.conversations_join(channel=channel_id)

auth_response = slack_app.client.auth_test()
bot_user_id = auth_response["user_id"]

# Customize this list based on the roles and interests in your organization
roles_and_interests = [
    "Software Engineer",
    "Product Manager",
    "Data Scientist",
    "Solution Architect",
    "Operations",
    "Security Specialist",
    "Educator",
]

blocks = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Welcome to OpenShift Commons! To get started, tell us about your role or interests:",
        }
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": role,
                },
                "action_id": f"select_{role.lower().replace(' ', '_')}",
            }
            for role in roles_and_interests
        ]
    },
]
   
@slack_app.command("/commons")
def handle_commons_command(ack, say, command, client):
    try:
        # Acknowledge the command request
        ack()

        user_id = command['user_id']  # Extract the user ID from the command
        channel_id = command['channel_id']  # Extract the channel ID from the command
        query = command['text']  # Extract the text part of the command which is the query

        print(f"Received commons query: {query}")

        # Example of sending an initial response
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="Processing your query... :thinking_face:"
        )

        # commons_agent = ReActAgent.from_tools(query_engine_tools, llm=llm, verbose=True, context=agentContext)
        # response = commons_agent.chat(query)
        # response_1 = query_engine_links.query(query)
        response_2 = query_engine_transcripts.query(query)
        # response = f"{response_1}\n\n{response_2}"
        response = response_2  # Formulate the response by joining response_1 and response_2
        # print("Context was:")
        # print(response_1.source_nodes)
        # print(response_2.source_nodes)

        formatted_response = convert_markdown_links_to_slack(str(response))
        print(f"Response: {formatted_response}")

        # Send response only to user
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=formatted_response
        )
    except Exception as e:
        # Send error reply in case of error
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"An error occurred, please try again later"
        )

@slack_app.message()
def reply(message, say, client):
    user_id = message['user']  # Extract the user ID from the message
    channel_id = message['channel']  # Extract the channel ID from the message
    blocks = message.get('blocks')
    thread_ts = message.get('thread_ts', None)  # Default to None if thread_ts isn't present
    print(blocks)

    if blocks:
        for block in blocks:
            if block.get('type') != 'rich_text':
                print("TYPE IS:" + block.get('type'))
                continue
            for rich_text_section in block.get('elements', []):
                elements = rich_text_section.get('elements', [])
                if any(element.get('type') == 'user' and element.get('user_id') == bot_user_id for element in elements):
                    for element in elements:
                        if element.get('type') == 'text':
                            query = element.get('text')
                            print(f"Somebody asked the bot: {query}")

                            client.chat_postEphemeral(
                                channel=channel_id,
                                user=user_id,
                                text="Thinking... :thinking_face:",  # Send the response text
                                thread_ts=thread_ts  # Include this to respond in the thread if the original message was part of one
                            )

                
                            try_count = 0
                            max_attempts = 5

                            while try_count < max_attempts:
                                try:
                                    commons_agent = ReActAgent.from_tools(query_engine_tools, llm=llm, verbose=True, context=agentContext)
                                    response = commons_agent.chat(query)

                                    formatted_response = convert_markdown_links_to_slack(str(response))
                                    
                                    print(f"Response was: {formatted_response}")
                                    
                                    # Send the final response visible to everyone in the channel
                                    client.chat_postMessage(
                                        channel=channel_id,
                                        text=str(formatted_response),
                                        thread_ts=thread_ts  # Include this to respond in the thread if the original message was part of one
                                    )
                                    
                                    break  # Exit the loop if successful
                                    
                                except Exception as e:
                                    print(f"An error occurred: {str(e)}")
                                    try_count += 1

                            if try_count == max_attempts:
                                formatted_response = "I'm sorry, something went wrong. Please try again later. Checkout the OpenShift commons website: https://commons.openshift.org/ for more information"
                                
                                client.chat_postMessage(
                                    channel=channel_id,
                                    text=str(formatted_response),
                                    thread_ts=thread_ts  # Include this to respond in the thread if the original message was part of one
                                )
                            return

    # dt_object = datetime.datetime.fromtimestamp(float(message.get('ts')))
    # formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
    # # otherwise do something else with it
    # print("Saw a fact: ", message.get('text'))
    #     # get the message text
    # text = message.get('text')
    #     # create a node with metadata
    # node = TextNode(
    #     text=text,
    #     id_=str(uuid.uuid4()),
    #     metadata={
    #         "when": formatted_time
    #     }
    # )
    # index.insert_nodes([node])


# Event, command, and action handlers
@slack_app.event("team_join")
def handle_member_joined_channel(event, client):
    user_id = event['user']['id']
    channel_id = user_id  # Direct message channel ID is the same as the user's ID
    client.chat_postMessage(channel=channel_id, blocks=blocks, text=f"Welcome <@{user_id}>")
 

# @slack_app.event("message")
# def handle_message_events(body, logger):
#     logger.info(body)
#     logger.info("We are handling a message")

@slack_app.command("/onboard")
def handle_onboard_command(ack, body, client):
    ack()
    user_id = body["user_id"]
    channel_id = body["channel_id"]
    thread_ts = body.get('thread_ts', None)  # Get thread_ts if present

    # Use chat_postEphemeral to send a message only visible to the user
    client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        blocks=blocks,
        thread_ts=thread_ts,
        text=f"Welcome <@{user_id}>"
    )

@slack_app.command("/help")
def handle_help_command(ack, body, client):
    ack() 

    user_id = body["user_id"]
    channel_id = body["channel_id"]

    # Define the help message with an additional section for asking questions
    help_message = """
*Here are the commands you can use with this Slack bot:*

- `/onboard`: Get started with the bot and set up your profile.
- `/help`: Show this help message.
- `/commons`: Ask a question to the bot about OpenShift Commons.

*Interactions:*
- Select your role from the buttons provided to get personalized channel recommendations.
- To ask questions and receive video recommendations, mention the bot with "@OpenShift Commons Team" followed by your question. For example, "@OpenShift Commons Team what are the latest insights on Kubernetes?" The bot will then search through OpenShift Commons videos and transcripts to provide you with relevant video links.

If you have any questions or need further assistance, feel free to ask here!
    """

    # Use chat_postEphemeral to send the help message only visible to the user who requested it
    client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=help_message
    )

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    # Respond to the Slack challenge
    if data and data.get("type") == "url_verification":
        return jsonify({
            "challenge": data.get("challenge")
        })
    
    return handler.handle(request)

@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    return handler.handle(request)


@flask_app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    print("Interactive")
    payload = json.loads(request.form["payload"])
    
    # Extract action_id from the payload
    action_id = payload["actions"][0]["action_id"]
    user_id = payload["user"]["id"]
    response_url = payload["response_url"]
    channel_id = payload['channel']['id']  # Ensure this is correctly extracted


    # Parse the role from the action_id
    role = action_id.split('select_')[1].replace('_', ' ').title()

    channel_suggestions = {
    "software engineer": [
        {"name": "bigdata_sig", "id": "C338UGHG8"},
        {"name": "imagebuilder_sig", "id": "C338V74DN"},
        {"name": "dotnet_sig", "id": "C343FF8SH"},
        {"name": "devops_sig", "id": "C34333SCC"},
        {"name": "openstack_sig", "id": "C34L30NK0"},
    ],
    "product manager": [
        {"name": "event", "id": "C0FNZ57NJ"},
    ],
    "data scientist": [
        {"name": "bigdata_sig", "id": "C338UGHG8"},
        {"name": "data_and_ai_sig", "id": "C8L8S4XFF"},
        {"name": "datascience-gathering-2021", "id": "C01L2ET3H50"},
    ],
    "solution architect": [
        {"name": "cloud-paks", "id": "C02E27BJD98"},
        {"name": "openstack_sig", "id": "C34L30NK0"},
        {"name": "operator-framework", "id": "CBA2X443E"},
    ],
    "operations": [
        {"name": "operations_sig", "id": "C34333SCC"},
        {"name": "operations-_sig", "id": "C343D9BBP"},
        {"name": "aws", "id": "CCL8BMY7J"},
    ],
    "security specialist": [
        {"name": "security_sig", "id": "C340W5L2E"},
        {"name": "gov_sig", "id": "C3409GB1Q"},
    ],
    "educator": [
        {"name": "edu_sig", "id": "C34LFK1K9"},
        {"name": "meetup-organizers", "id": "C015THC4KMW"},
    ],
}

    channel_names_id = channel_suggestions.get(role.lower(), [])
    suggested_channels = [{"name": name_id['name'], "id": name_id['id']} for name_id in channel_names_id]
    suggested_channels = [channel for channel in suggested_channels if channel['id'] is not None]
    suggested_channels_text = "\n".join([f"- <#{channel['id']}|{channel['name']}>" for channel in suggested_channels])
    kubecon_paris = {"name": "kubecon_paris", "id": "C06HFFNHVPA"}


    help_message = """
*Here are more things you can do:*

- `/help`: Show this help message.
- `/commons`: Ask a question to the bot about OpenShift Commons that is only visible to you.
- Ask questions and receive recommendation, mention the bot with "@OpenShift Commons Team" followed by your question. For example, "@OpenShift Commons Team what are the latest insights on Kubernetes?" 
The bot will then search through it's knowledge to provide you with relevant information.

If you have any questions or need further assistance, feel free to ask here! Also make sure to check https://commons.openshift.org/ for more information.
    """

    # Prepare the response message
    response_text = f"<@{user_id}> based on your interest in {role}, we suggest you join the following channels:\n{suggested_channels_text}"
    response_text += f"\n- <#{kubecon_paris['id']}|{kubecon_paris['name']}> (also check out KubeCon Paris Channel)"
# append response_text with help_message to use the bot 
    response_text += f"\n\n{help_message}"

    # create slack_client
    slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    # Use chat_postEphemeral to send a reply only visible to the user
    slack_client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=response_text  # Pass the response_text string here
    )

    # send_response_to_slack(response_url=response_url, message=message)
    return jsonify({})


def send_response_to_slack(response_url, message):
    webhook = WebhookClient(response_url)
    response = webhook.send(text=message["text"])

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print(f"Failed to send message, error: {response.status_code}, {response.body}")


if __name__ == "__main__":
    port = os.getenv("PORT", 10000)
    flask_app.run(host='0.0.0.0', debug=True, port=port)
