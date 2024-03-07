import json
import logging
import os
import sys
from nest_asyncio import apply
import threading

from dotenv import load_dotenv
from flask import Flask, request, jsonify

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient, WebhookClient

from utils import convert_markdown_links_to_slack
from index import IndexManager
from loaders import QdrantClientManager, EnvironmentConfig, YouTubeLoader
from query_engine import QueryEngineManager, QueryEngineToolsManager

from llama_index.core import Settings, ServiceContext
from llama_index.core.node_parser import (
    # TokenTextSplitter,
    # SemanticSplitterNodeParser,
    SentenceSplitter
)

from llama_index.core.agent.react import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

from graphsignal import configure

Settings.llm = OpenAI(model="gpt-4", temperature=0.1, stop_symbols=["\n"])
# Settings.llm = OpenAI(model="gpt-4-turbo-preview", temperature=0.1, stop_symbols=["\n"])
# set llm as gpt-3.5-turbo for faster response time
# change to gpt-4-turn
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
# Settings.node_parser = TokenTextSplitter(chunk_size=1024, chunk_overlap=200),
# Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)
# Settings.num_output = 512
# Settings.context_window = 3900

configure(api_key=os.environ['GRAPH_SIGNAL_API_KEY'], deployment='commons-bot')

# Load environment variables from .env file or Lambda environment
load_dotenv()
apply()

# even noisier debugging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

collection_name = "commons-clean"
config = EnvironmentConfig()
qdrant_manager = QdrantClientManager(config, collection_name)
qdrant_client = qdrant_manager.client

# Assuming 'client' is your initialized Qdrant client and 'youtube_transcripts' is your data
# llm = OpenAI(model="gpt-4", temperature=0.0, stop_symbols=["\n"])

# set chunk_size to 1024 higher relevancy and faithfulness (according to evaluation)
# values referencing a similar use-case for transcripts: https://neo4j.com/developer-blog/youtube-transcripts-knowledge-graphs-rag/ 
## TODO - refactor to remove redundancy between service_context and the new "Settings" attribute in 0.10.x

# semantic_node_parser = SemanticSplitterNodeParser(
#     buffer_size=1, breakpoint_percentile_threshold=95, embed_model=Settings.embed_model
# )
# text_node_parser = TokenTextSplitter(chunk_size=1024, chunk_overlap=200)
sentence_node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)

service_context = ServiceContext.from_defaults(
    llm=Settings.llm,
    embed_model=Settings.embed_model,
    node_parser=sentence_node_parser
)

index_manager = IndexManager(qdrant_client, service_context, embed_model=Settings.embed_model,
                             collection_name=collection_name)
index = index_manager.create_or_load_index()

## testing stuff
# index_manager.splitter(documents=YouTubeLoader().yttranscripts)
# index_manager.retriever(index)
## end of testing 

query_engine_manager = QueryEngineManager(index)
query_engine_transcripts = query_engine_manager.create_query_engine()

agent_context = query_engine_manager.get_agent_context()
agent_commands_context = query_engine_manager.get_agent_commands_context()

query_engine_tools_manager = QueryEngineToolsManager(query_engine_transcripts)
query_engine_agent_tools = query_engine_tools_manager.query_engine_agent_tools
query_engine_agent_commands_tools = query_engine_tools_manager.query_engine_command_tools

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
    user_id = command['user_id']  # Extract the user ID from the command
    command_channel_id = command['channel_id']  # Extract the channel ID from the command
    query = command['text']  # Extract the text part of the command which is the query
    ack()  # Acknowledge the command request immediately

    client.chat_postEphemeral(
        channel=command_channel_id,
        user=user_id,
        text="Got your command, working on it! :hourglass_flowing_sand:"
    )

    max_attempts = 5
    query_engine_response = ""
    # Process and send the transcripts response with retry mechanism
    try_count = 0
    while try_count < max_attempts:
        try:
            response_transcripts = query_engine_transcripts.query(query)
            formatted_transcripts_response = convert_markdown_links_to_slack(str(response_transcripts))

            client.chat_postEphemeral(
                channel=command_channel_id,
                user=user_id,
                text=formatted_transcripts_response
            )
            query_engine_response = formatted_transcripts_response
            break  # Exit the loop if successful
        except Exception as e:
            print(f"Transcripts error: {str(e)}")
            try_count += 1

    if try_count == max_attempts:
        client.chat_postEphemeral(
            channel=command_channel_id,
            user=user_id,
            text="An error occurred while processing the transcripts response, please try again later."
        )

    client.chat_postEphemeral(
        channel=command_channel_id,
        user=user_id,
        text="Getting you more information :information_source:"
    )

    # Process and send the agent response with retry mechanism
    try_count = 0
    while try_count < max_attempts:
        try:
            commons_agent = ReActAgent.from_tools(query_engine_agent_commands_tools, llm=Settings.llm, verbose=True,
                                                  context=agent_commands_context)

            # use the response from the transcripts query engine to amplify the agent response
            response_agent = commons_agent.chat(query_engine_response)
            formatted_agent_response = convert_markdown_links_to_slack(str(response_agent))

            client.chat_postEphemeral(
                channel=command_channel_id,
                user=user_id,
                text=formatted_agent_response
            )
            break  # Exit the loop if successful
        except Exception as e:
            print(f"Agent error: {str(e)}")
            try_count += 1

    if try_count == max_attempts:
        client.chat_postEphemeral(
            channel=command_channel_id,
            user=user_id,
            text="An error occurred while processing the agent response, please try again later."
        )


@slack_app.message()
def reply(message, say, client):
    user_id = message['user']  # Extract the user ID from the message
    reply_channel_id = message['channel']  # Extract the channel ID from the message
    reply_blocks = message.get('blocks')
    thread_ts = message.get('thread_ts', None)  # Default to None if thread_ts isn't present
    # print(blocks)
    # print("handling message")

    if reply_blocks:
        for block in reply_blocks:
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

                            client.reactions_add(
                                name="hourglass_flowing_sand",
                                channel=reply_channel_id,
                                timestamp=message['ts']
                            )

                            client.chat_postEphemeral(
                                channel=reply_channel_id,
                                user=user_id,
                                text="Got your message, working on it! :hourglass_flowing_sand:",
                                # Send the response text
                                thread_ts=thread_ts
                            )

                            max_attempts = 5

                            # Query and send the transcripts response with retry mechanism
                            try_count = 0
                            while try_count < max_attempts:
                                try:
                                    response_transcripts = query_engine_transcripts.query(query)
                                    formatted_transcripts_response = convert_markdown_links_to_slack(
                                        str(response_transcripts))

                                    client.chat_postMessage(
                                        channel=reply_channel_id,
                                        text=formatted_transcripts_response,
                                        thread_ts=thread_ts or message['ts']
                                    )

                                    break  # Exit the loop if successful
                                except Exception as e:
                                    print(f"Transcripts error: {str(e)}")
                                    try_count += 1

                            if try_count == max_attempts:
                                client.chat_postEphemeral(
                                    channel=reply_channel_id,
                                    user=user_id,
                                    text="An error occurred while processing the transcripts response, please try again later."
                                )

                            # Inform the user that more information is being retrieved
                            client.chat_postEphemeral(
                                channel=reply_channel_id,
                                user=user_id,
                                text="Getting you more information :information_source:"
                            )

                            try_count = 0
                            while try_count < max_attempts:
                                try:
                                    commons_agent = ReActAgent.from_tools(query_engine_agent_commands_tools,
                                                                          llm=Settings.llm,
                                                                          verbose=True, context=agent_commands_context)
                                    response_agent = commons_agent.chat(query)
                                    formatted_response = convert_markdown_links_to_slack(str(response_agent))

                                    print(f"Response was: {formatted_response}")

                                    # Send the final response visible to everyone in the channel
                                    client.chat_postMessage(
                                        channel=reply_channel_id,
                                        text=str(formatted_response),
                                        thread_ts=thread_ts or message['ts']
                                    )

                                    break  # Exit the loop if successful

                                except Exception as e:
                                    print(f"An error occurred: {str(e)}")
                                    try_count += 1

                            if try_count == max_attempts:
                                formatted_response = "I'm sorry, something went wrong. Please try again later. In the mean time, checkout the OpenShift commons website: https://commons.openshift.org/ for more information"

                                client.chat_postMessage(
                                    channel=reply_channel_id,
                                    text=str(formatted_response),
                                    thread_ts=thread_ts or message['ts']
                                )

                            # remove reaction                                     
                            client.reactions_remove(
                                name="hourglass_flowing_sand",
                                channel=reply_channel_id,
                                timestamp=message['ts']
                            )

                            client.reactions_add(
                                name="white_check_mark",
                                channel=reply_channel_id,
                                timestamp=message['ts']
                            )
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
    direct_channel_id = user_id  # Direct message channel ID is the same as the user's ID
    client.chat_postMessage(channel=direct_channel_id, blocks=blocks, text=f"Welcome <@{user_id}>")


# @slack_app.event("message")
# def handle_message_events(body, logger):
#     logger.info(body)
#     logger.info("We are handling a message")

@slack_app.command("/onboard")
def handle_onboard_command(ack, body, client):
    ack()
    user_id = body["user_id"]
    onboard_channel_id = body["channel_id"]
    thread_ts = body.get('thread_ts', None)  # Get thread_ts if present

    # Use chat_postEphemeral to send a message only visible to the user
    client.chat_postEphemeral(
        channel=onboard_channel_id,
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

* `/onboard`: Get started with the bot and set up your profile.
* `/help`: Show this help message.
* `/commons`: Ask a question to the bot about OpenShift Commons.

*Interactions:*
* Select your role from the buttons provided to get personalized channel recommendations.
* To ask questions and receive video recommendations, mention the bot with "@OpenShift Commons Team" followed by your question. For example, "@OpenShift Commons Team what are the latest insights on Kubernetes?" The bot will then search through OpenShift Commons videos and transcripts to provide you with relevant video links.

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
-  Ask questions and receive recommendations, mention the bot with "@OpenShift Commons Team" followed by your question. For example, "@OpenShift Commons Team what are the latest insights on Kubernetes?" 
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
