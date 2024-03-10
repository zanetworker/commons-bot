import json
import logging
import os
import sys
from nest_asyncio import apply
from dotenv import load_dotenv
from flask import Flask, request, jsonify

from slack_sdk import WebClient, WebhookClient
import slack

from index import IndexManager
from loaders import QdrantClientManager, EnvironmentConfig
from query_engine import QueryEngineManager, QueryEngineToolsManager

from llama_index.core import Settings, ServiceContext
from llama_index.core.node_parser import (
    # TokenTextSplitter,
    # SemanticSplitterNodeParser,
    SentenceSplitter
)

from llama_index.core.agent.react import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama

from llama_index.embeddings.openai import OpenAIEmbedding

from graphsignal import configure

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
import threading
import os

# Settings.llm = OpenAI(model="gpt-4", temperature=0.1, stop_symbols=["\n"])
# Settings.llm = OpenAI(model="gpt-4-turbo-preview", temperature=0.1, stop_symbols=["\n"])
# change to gpt-4-1106-preview
# Settings.llm = OpenAI(model="gpt-4-1106-preview", temperature=0.1, stop_symbols=["\n"])
Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0.1, stop_symbols=["\n"])

# Settings.llm = Ollama(model="llama2", request_timeout=240.0, base_url="http://192.168.178.254:11434")

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

# Flask app to handle requests
flask_app: Flask = Flask(__name__)

# Initializes your app with your bot token and signing secret
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

# only enable to join specific channels
# channel_list = slack_app.client.conversations_list().data
# channel = next((channel for channel in channel_list.get('channels') if channel.get("name") == "test-bot"), None)
# channel_id = channel.get('id')
# slack_app.client.conversations_join(channel=channel_id)


handler = SlackRequestHandler(slack_app)

slack_ops = slack.SlackOperations(slack_app)
message_handler = slack.MessageHandler(slack_ops, query_engine_transcripts, query_engine_agent_commands_tools,
                                       agent_commands_context)

# Initialize Command Handlers with Slack Operations
cmd_handler = slack.CommandHandler(slack_ops, query_engine_transcripts, query_engine_agent_commands_tools,
                                   agent_commands_context)

# Register command handlers
slack_app.command("/commons")(cmd_handler.handle_commons_command)
slack_app.command("/onboard")(cmd_handler.handle_onboard_command)
slack_app.command("/help")(cmd_handler.handle_help_command)

# pass challenge
auth_response = slack_app.client.auth_test()
bot_user_id = auth_response["user_id"]


@slack_app.message()
def handle_incoming_messages(message, say):
    message_handler.handle_message(message, say, slack_app.client)


# Event, command, and action handlers
@slack_app.event("team_join")
def handle_member_joined_channel(event, client):
    user_id = event['user']['id']
    direct_channel_id = user_id  # Direct message channel ID is the same as the user's ID
    client.chat_postMessage(channel=direct_channel_id, blocks=slack.blocks, text=f"Welcome <@{user_id}>")


def _parse_payload(payload):
    """Extracts and returns relevant information from the payload."""
    action_id = payload["actions"][0]["action_id"]
    role = action_id.split('select_')[1].replace('_', ' ').title()
    user_id = payload["user"]["id"]
    channel_id = payload['channel']['id']
    return role, user_id, channel_id


def _get_suggested_channels(role):
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

    """Returns a formatted string of suggested channels based on the role."""
    channel_ids_names = channel_suggestions.get(role.lower(), [])
    suggested_channels = [f"- <#{ch['id']}|{ch['name']}>" for ch in channel_ids_names if ch['id']]
    return "\n".join(suggested_channels)


def _construct_response_text(user_id, role, suggested_channels_text):
    help_message = """
    *Here are more things you can do:*

    - `/help`: Show this help message.
    - `/commons`: Ask a question to the bot about OpenShift Commons that is only visible to you.
    -  Ask questions and receive recommendations, mention the bot with "@OpenShift Commons Team" followed by your question. For example, "@OpenShift Commons Team what are the latest insights on Kubernetes?" 
    The bot will then search through it's knowledge to provide you with relevant information.

    If you have any questions or need further assistance, feel free to ask here! Also make sure to check https://commons.openshift.org/ for more information.
        """
    kubecon_paris = {"name": "kubecon_paris", "id": "C06HFFNHVPA"}
    return (f"<@{user_id}> based on your interest in {role}, we suggest you join the following channels:\n"
            f"{suggested_channels_text}\n"
            f"- <#{kubecon_paris['id']}|{kubecon_paris['name']}> (also check out KubeCon Paris Channel)\n\n"
            f"{help_message}")


@flask_app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    print("Interactive")
    payload = json.loads(request.form["payload"])
    role, user_id, channel_id = _parse_payload(payload)
    suggested_channels_text = _get_suggested_channels(role)
    response_text = _construct_response_text(user_id, role, suggested_channels_text)

    # Assuming slack_ops is an instance of a class that handles Slack operations
    slack_ops.post_ephemeral_message(channel_id, user_id, response_text)

    return jsonify({})


@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    return handler.handle(request)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    # Respond to the Slack challenge
    if data and data.get("type") == "url_verification":
        return jsonify({
            "challenge": data.get("challenge")
        })

    return handler.handle(request)


if __name__ == "__main__":
    port = os.getenv("PORT", 10000)
    flask_app.run(host='0.0.0.0', debug=True, port=port)
