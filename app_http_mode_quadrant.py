import json
import logging
import os
import re
import sys
import datetime, uuid
from pathlib import Path


from dotenv import load_dotenv
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient, WebhookClient


# import qdrant_client
import chromadb
import qdrant_client 

# import qdrant_client
from llama_index.vector_stores import QdrantVectorStore
from llama_index.schema import TextNode
from llama_index.prompts import PromptTemplate
# from llama_index.postprocessor import FixedRecencyPostprocessor
from llama_index import download_loader
from llama_hub.youtube_transcript import YoutubeTranscriptReader
from llama_index import VectorStoreIndex, Document, StorageContext, ServiceContext

from llama_index.llms import OpenAI


# Load environment variables from .env file or Lambda environment
load_dotenv()

# even noisier debugging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# initialize index
def get_qdrant_client():
    return qdrant_client.QdrantClient(path="./qdrant_data")

def load_youtube_links():
    PandasExcelReader = download_loader("PandasExcelReader")
    loader = PandasExcelReader(pandas_config={"header": 0})
    return loader.load_data(file=Path('./data/commons_videos.xlsx'))

def load_youtube_transcripts():
    loader = YoutubeTranscriptReader()
    ytlinks = [
    'https://www.youtube.com/watch?v=RzxzY1dluvo',
    'https://www.youtube.com/watch?v=ZTsgcnxQyw4',
    'https://www.youtube.com/watch?v=m-p7jmXoQdk', 
    'https://www.youtube.com/watch?v=6PZfKufNisM',
    'https://www.youtube.com/watch?v=-Ma4FBOtdbo',
    'https://www.youtube.com/watch?v=eEwQeLns_hU',
    'https://www.youtube.com/watch?v=njscOv2wJeA',
    'https://www.youtube.com/watch?v=i5BmIJSaduk',
    'https://www.youtube.com/watch?v=4_3B0lAsXWQ',
    'https://www.youtube.com/watch?v=ZOKJWp3GfRs',
    'https://www.youtube.com/watch?v=iLaMDtf7hqk',
    'https://www.youtube.com/watch?v=E5gnj61MyhM',
    'https://www.youtube.com/watch?v=0ZnzZpU7K8w',
    'https://www.youtube.com/watch?v=NdZ8zuqaT8U',
    'https://www.youtube.com/watch?v=8L-IdpEUGxU',
    'https://www.youtube.com/watch?v=6Os9JMNCDXY',
    'https://www.youtube.com/watch?v=Nw3eMHWDCUc',
    'https://www.youtube.com/watch?v=M2rdwyFzx2M',
    # 'https://www.youtube.com/watch?v=YFSJIwboOjk',
    'https://www.youtube.com/watch?v=HDkwtVbuL1w',
    'https://www.youtube.com/watch?v=IMs9gdXXB1s',
    'https://www.youtube.com/watch?v=K1KNXzOTK-0',
    'https://www.youtube.com/watch?v=WyA_hts7XMs',
    'https://www.youtube.com/watch?v=3dkyD3u6iP4',
    'https://www.youtube.com/watch?v=n3epPdiOOOM',
    'https://www.youtube.com/watch?v=TJPOR98MKV8',
    'https://www.youtube.com/watch?v=pKEi_o2mA40',
    'https://www.youtube.com/watch?v=qNgtxU5XOrg',
    'https://www.youtube.com/watch?v=aVq69JzC6jM',
    'https://www.youtube.com/watch?v=_3IfYLb_bbE', 
    # 'https://www.youtube.com/watch?v=UXls_JfzyG8',
    # 'https://www.youtube.com/watch?v=ciCncHHadlo'
]
    return loader.load_data(ytlinks=ytlinks)

def create_or_load_index(documents, vector_store_path = "./qdrant_data", chunk_size=1000, db=False):
    vector_store_exists = os.path.exists(vector_store_path)
    index = None
    llm = OpenAI(model="gpt-4", temperature=0.0)
    service_context = ServiceContext.from_defaults(llm=llm, chunk_size=chunk_size)

    client = qdrant_client.QdrantClient(path="./qdrant_data")
    vector_store = QdrantVectorStore(client=client, collection_name="text_docs", service_context=service_context)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if vector_store_exists: 
        index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context, service_context=service_context)
    else:
        index = VectorStoreIndex.from_documents(documents, storage_context=storage_context, service_context=service_context)

    return index

def create_query_engine(index, similarity_top_k=2, streaming=True, chat=False):
    return index.as_chat_engine(streaming=streaming) if chat else index.as_query_engine(similarity_top_k=similarity_top_k, streaming=streaming)

youtube_video_links = load_youtube_links()
youtube_transcripts = load_youtube_transcripts()

index = create_or_load_index(youtube_video_links)
index_transcripts = create_or_load_index(youtube_transcripts)

query_engine_links = create_query_engine(index, chat=False)
query_engine_transcripts = create_query_engine(index_transcripts, chat=False)

template = (
    "Your context is a list of urls for OpenShift commons videos. Each input has a url, and a title for the video \n"
    "indicating what the video was abput \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "You are a helpful AI assistant who can tell me which video is best matching to my query. \n"
    "give me the most relevant video from the context I gave you: {query_str}\n"
)

template_transcripts = (
    "Your context is a list of youtube transcripts. Each transcript is for a video that talks about a certain topic \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "You are a helpful AI assistant who can pick the best information from the transcripts. \n"
    "give me the most relevant information from the best transcript in the form of a paragraph. Start your reply with \"here is some additional information you might like\" \n" 
    "and share the URL of the video you got the infromation from: {query_str}\n"
)

qa_template = PromptTemplate(template)   
qa_template_transcripts = PromptTemplate(template_transcripts)

query_engine_links.update_prompts(
        {"response_synthesizer:text_qa_template": qa_template}
)
query_engine_transcripts.update_prompts(
        {"response_synthesizer:text_qa_template": qa_template_transcripts}
)

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
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

@slack_app.message()
def reply(message, say):
    blocks = message.get('blocks')
    print(blocks)
    if blocks:
        for block in blocks:
            if block.get('type') != 'rich_text':
                continue
            for rich_text_section in block.get('elements', []):
                elements = rich_text_section.get('elements', [])
                if any(element.get('type') == 'user' and element.get('user_id') == bot_user_id for element in elements):
                    for element in elements:
                        if element.get('type') == 'text':
                            query = element.get('text')
                            print(f"Somebody asked the bot: {query}")
                            response_1 = query_engine_links.query(query)
                            response_2 = query_engine_transcripts.query(query)
                            # formulate a repsonse the joins response_1 and response_2 nicely without using "+" operator
                            response = str(response_1) + "\n\n" + str(response_2)
                            print("Context was:")
                            print(response_1.source_nodes)
                            print(response_2.source_nodes)

                            print(f"Response was: {response}")
                            say(response)
                            return
   
   
    dt_object = datetime.datetime.fromtimestamp(float(message.get('ts')))
    formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
    # otherwise do something else with it
    print("Saw a fact: ", message.get('text'))
        # get the message text
    text = message.get('text')
        # create a node with metadata
    node = TextNode(
        text=text,
        id_=str(uuid.uuid4()),
        metadata={
            "when": formatted_time
        }
    )
    index.insert_nodes([node])


# Event, command, and action handlers
@slack_app.event("team_join")
def handle_member_joined_channel(event, client):
    user_id = event['user']['id']
    channel_id = user_id  # Direct message channel ID is the same as the user's ID
    client.chat_postMessage(channel=channel_id, blocks=blocks, text=f"Welcome <@{user_id}>")
 

@slack_app.event("message")
def handle_message_events(body, logger):
    logger.info(body)
    logger.info("We are handling a message")

# Handling '/onboard' command
@slack_app.command("/onboard")
def handle_onboard_command(ack, body, say):
    ack()
    user_id = body["user_id"]
    channel_id = body["channel_id"]

    say(blocks=blocks, text=f"Welcome <@{user_id}>", channel=channel_id)

# Handling role selection action
@slack_app.action(re.compile("select_(.*)"))
def handle_role_selection(ack, body, say):
    ack()
    action_id = body['actions'][0]['action_id']
    role = action_id.split('select_')[1].replace('_', ' ').title()  # Capitalize the role

    user_id = body["user"]["id"]

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
        {"name": "marketing", "id": "CXXXXXXX1"},
        {"name": "product", "id": "CXXXXXXX2"},
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

    say(
        text=f"<@{user_id}> based on your interest in {role}, we suggest you join the following channels:\n{suggested_channels_text}"
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
        {"name": "marketing", "id": "CXXXXXXX1"},
        {"name": "product", "id": "CXXXXXXX2"},
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

    # Find the suggested channels for the role
    channel_names_id = channel_suggestions.get(role.lower(), [])
    suggested_channels = [{"name": name_id['name'], "id": name_id['id']} for name_id in channel_names_id]
    suggested_channels = [channel for channel in suggested_channels if channel['id'] is not None]
    suggested_channels_text = "\n".join([f"- <#{channel['id']}|{channel['name']}>" for channel in suggested_channels])

    # Prepare the response message
    message = {
        "text": f"<@{user_id}> based on your interest in {role}, we suggest you join the following channels:\n{suggested_channels_text}"
    }

    send_response_to_slack(response_url=response_url, message=message)
    return jsonify({})

@flask_app.route('/hello', methods=['GET'])
def hello():
    return "Hello, World!"


def send_response_to_slack(response_url, message):
    webhook = WebhookClient(response_url)
    response = webhook.send(text=message["text"])

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print(f"Failed to send message, error: {response.status_code}, {response.body}")


if __name__ == "__main__":
    flask_app.run(debug=True, port=5002)
