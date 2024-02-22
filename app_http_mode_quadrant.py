import json
import logging
import os
import re
import sys
import datetime, uuid
from pathlib import Path
import nest_asyncio
from tool_specs import SlackToolSpec, FeedSpec

from dotenv import load_dotenv
from flask import Flask, request, jsonify

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient, WebhookClient

# import qdrant_client
from qdrant_client import QdrantClient
from qdrant_client.http import models

# import qdrant_client
from llama_index.vector_stores import QdrantVectorStore
from llama_index.schema import TextNode
from llama_index.prompts import PromptTemplate
from llama_index.tools import QueryEngineTool, ToolMetadata
from llama_index.agent import ReActAgent
from llama_index import VectorStoreIndex,load_index_from_storage,  Document, StorageContext, ServiceContext, download_loader
from llama_index.llms import OpenAI

from llama_hub.youtube_transcript import YoutubeTranscriptReader

import graphsignal

graphsignal.configure(api_key=os.environ['GRAPH_SIGNAL_API_KEY'], deployment='commons-bot')

# Load environment variables from .env file or Lambda environment
load_dotenv()
nest_asyncio.apply()

# even noisier debugging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# initialize index
def get_qdrant_client():
    return QdrantClient(path="./qdrant_data")

def get_qdrant_cloud_client():
    return  QdrantClient(
    url=os.environ["QD_ENDPOINT"], 
    api_key=os.environ["QD_API_KEY"],
)

def load_youtube_links():
    PandasExcelReader = download_loader("PandasExcelReader")
    loader = PandasExcelReader(pandas_config={"header": 0})
    return loader.load_data(file=Path('./data/commons_urls.xlsx'))

def load_youtube_transcripts():
    loader = YoutubeTranscriptReader()
    ytlinks = [
    'https://youtu.be/ZxvbQbT_wkc?feature=shared',   
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
    'https://www.youtube.com/watch?v=3vjOCOLXExQ',
    'https://www.youtube.com/watch?v=zcO2qR2dbdo',
    'https://www.youtube.com/watch?v=RCwcEZtba4E',
    'https://www.youtube.com/watch?v=bIruzpvRe74',
    'https://www.youtube.com/watch?v=9YLMf-d_Kqk',
    'https://www.youtube.com/watch?v=lojstGGfB3E',
    'https://www.youtube.com/watch?v=M6bqUfIecKA',
    'https://www.youtube.com/watch?v=lQHMRXGB_pY',
    'https://www.youtube.com/watch?v=RYP6ZntTby4',
    'https://www.youtube.com/watch?v=eT5Dz3fziQY',
    'https://www.youtube.com/watch?v=Q05O1H0UxaI',
    'https://www.youtube.com/watch?v=1082Lke8rz0',
    'https://www.youtube.com/watch?v=PTo2soO20Fs',
    'https://www.youtube.com/watch?v=L4tk3b5uTEI',
    'https://www.youtube.com/watch?v=tnmoGz9JBQA',
    'https://www.youtube.com/watch?v=nJJdfw_ymfU',
    'https://www.youtube.com/watch?v=fJXRHsxLnI4',
    'https://www.youtube.com/watch?v=tissYjujjiE',
    'https://www.youtube.com/watch?v=mpzr_HOPSkE',
    'https://www.youtube.com/watch?v=7rl1OVUlx1k',
    'https://www.youtube.com/watch?v=MKSzBZ3-mvQ',
    'https://www.youtube.com/watch?v=csgCyfnq7qs',
    'https://www.youtube.com/watch?v=N4tt8_VP1o0',
    'https://www.youtube.com/watch?v=yl5MtiQqbsQ',
    'https://www.youtube.com/watch?v=tVSPTrf_JXU',
    'https://www.youtube.com/watch?v=r75lTd_lKyQ',
    'https://www.youtube.com/watch?v=AKPB2IQ-ew0',
    'https://www.youtube.com/watch?v=ZYXAfCCEKS0',
    'https://www.youtube.com/watch?v=JcdB55yLGbg',
    'https://www.youtube.com/watch?v=lHkZOu0EMys',
    'https://www.youtube.com/watch?v=MYyikxV0l-o',
    'https://www.youtube.com/watch?v=OqGfwy0d7b8',
    'https://www.youtube.com/watch?v=e86IbJaPIFQ',
    'https://www.youtube.com/watch?v=PuMA5OrJtXo',
    'https://www.youtube.com/watch?v=Kk5SRhxSCmM',
    'https://www.youtube.com/watch?v=aELiz-g12dk',
    'https://www.youtube.com/watch?v=Gf0d7q4ZEfw',
    'https://www.youtube.com/watch?v=XO2k1oqy9qU',
    'https://www.youtube.com/watch?v=5a377Rda79U',
    'https://www.youtube.com/watch?v=dIG3gLmDRXg',
    'https://www.youtube.com/watch?v=TqpNf1xt2ZQ',
    'https://www.youtube.com/watch?v=0bqwVuSV9ho',
    'https://www.youtube.com/watch?v=UejmEiAptFE',
    'https://www.youtube.com/watch?v=_Gft7jkmxTI',
    'https://www.youtube.com/watch?v=8_6MQdtd2ww',
    'https://www.youtube.com/watch?v=fe-OhqT_kxA',
    'https://www.youtube.com/watch?v=SKbA4b2JZOg',
    'https://www.youtube.com/watch?v=anaB7pBL9uU',
    'https://www.youtube.com/watch?v=cJUunrXVT50',
    'https://www.youtube.com/watch?v=OXPkHNoWOec',
    'https://www.youtube.com/watch?v=1KNFnQG2b5w',
    'https://www.youtube.com/watch?v=Mz4R4iDDm0M',
    'https://www.youtube.com/watch?v=HfsJqqjmiZo',
    'https://www.youtube.com/watch?v=1ddxwZWSgtY',
    'https://www.youtube.com/watch?v=J_c2_yBJ5bs',
    'https://www.youtube.com/watch?v=KizNQTpRA2A',
    'https://www.youtube.com/watch?v=3S855TdwhH4',
    'https://www.youtube.com/watch?v=_Cug1C744Ug',
    'https://www.youtube.com/watch?v=FZNcX2SosjU',
    'https://www.youtube.com/watch?v=tfnHap8K9cM',
    'https://www.youtube.com/watch?v=kBmLBHc16eA',
    'https://www.youtube.com/watch?v=YF3S9WqWZpU',
    'https://www.youtube.com/watch?v=KQmiM06tsEE',
    'https://www.youtube.com/watch?v=S6Obo7pw6p4',
    'https://www.youtube.com/watch?v=Tt0RlJYrcC8',
    'https://www.youtube.com/watch?v=p1UNdLqJ9sQ',
    'https://www.youtube.com/watch?v=lsltHGUZ6nE',
    'https://www.youtube.com/watch?v=aq1VFOiLi_0',
    'https://www.youtube.com/watch?v=v6s5KznHULs',
    'https://www.youtube.com/watch?v=4L0R6Ews5uY',
    'https://www.youtube.com/watch?v=b-QtgBEgt-c',
    'https://www.youtube.com/watch?v=U1e7nRA843E',
    'https://www.youtube.com/watch?v=mvcPzQHpUW0',
    'https://www.youtube.com/watch?v=vae2Wx5LLYg',
    'https://www.youtube.com/watch?v=vQUhtN0Vjro',
    'https://www.youtube.com/watch?v=4_Duwdhi1aA',
    'https://www.youtube.com/watch?v=c2suFsA4Evw',
    'https://www.youtube.com/watch?v=6BD3pknWwvY',
    'https://www.youtube.com/watch?v=T1YSBXP9T9s',
    'https://www.youtube.com/watch?v=szEz9Ocnao0',
    'https://www.youtube.com/watch?v=dJe857oQV4Q',
    'https://www.youtube.com/watch?v=LrIvFQaq_Zo',
    'https://www.youtube.com/watch?v=awgmTOLxYOE',
    'https://www.youtube.com/watch?v=X8eg0RuGYG0',
    'https://www.youtube.com/watch?v=-MNGRqubMw4',
    'https://www.youtube.com/watch?v=Nwz2aGoqjE0',
    'https://www.youtube.com/watch?v=y0_-CAcRnUk',
    'https://www.youtube.com/watch?v=o-qae0vJ3Aw',
    'https://www.youtube.com/watch?v=kMnIGSb3T8w',
    'https://www.youtube.com/watch?v=mWdglzUb6vY',
    'https://www.youtube.com/watch?v=6YMfzqHXfqg',
    'https://www.youtube.com/watch?v=ZIKq0W9z31I',
    'https://www.youtube.com/watch?v=-PCLnEoIZp4',
    'https://www.youtube.com/watch?v=i5wd_qZdc8Y',
    'https://www.youtube.com/watch?v=SVk_IIT0O2E',
    'https://www.youtube.com/watch?v=SESq3OZxNBY',
    'https://www.youtube.com/watch?v=DhpDqa7oxzI',
    'https://www.youtube.com/watch?v=fnH60GhaZ1w',
    'https://www.youtube.com/watch?v=5cueeNm667U',
]
    return loader.load_data(ytlinks=ytlinks)

def load_index(vector_store, storage_context, service_context):
    return VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context, service_context=service_context)

def create_index(documents, storage_context, service_context):
    return VectorStoreIndex.from_documents(documents, storage_context=storage_context, service_context=service_context)

def create_query_engine(index, similarity_top_k=5, streaming=True, chat=False):
    return index.as_chat_engine(streaming=streaming, similarity_top_k=similarity_top_k) if chat else index.as_query_engine(similarity_top_k=similarity_top_k, streaming=streaming)

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

llm = OpenAI(model="gpt-4-turbo-preview", temperature=0.0, stop=["\n"])
# llm = OpenAI(model="gpt-4", temperature=0.0, stop=["\n", "Here is the URL of the video you might like:"])

# llm = OpenAI(model="gpt-3.5-turbo-0613", temperature=0.0, max_tokens=100, top_p=1.0, frequency_penalty=0.0, presence_penalty=0.0, stop=["\n", "Here is the URL of the video you might like:"])

service_context = ServiceContext.from_defaults(llm=llm, chunk_size=1000)

collection = "commons"
client = get_qdrant_cloud_client()

collection_exists = False
try: 
    collection_exists = client.get_collection(collection_name=collection)
except: 
    client.create_collection(
        collection_name=collection,
        # OpenAI embedding is 1536, Gemini is 768 (we need to adjust vector size accordingly)
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
)

vector_store = QdrantVectorStore(client=client, collection_name=collection, service_context=service_context)
storage_context = StorageContext.from_defaults(vector_store=vector_store)


index = None
index_transcripts = None

if not collection_exists:
    print("Collection does not exist, creating new index")
    # youtube_video_links = load_youtube_links()
    youtube_transcripts = load_youtube_transcripts()
    # index = create_index(documents=youtube_video_links, storage_context=storage_context, service_context=service_context)
    index_transcripts = create_index(documents=youtube_transcripts, storage_context=storage_context, service_context=service_context)
else:
    print("Collection does exist, loading index from storage")
    # Run refresh_ref_docs method to check for document updates

    index = load_index(vector_store=vector_store, storage_context=storage_context, service_context=service_context)
    index_transcripts = index # use the same index for both links and transcripts


# query_engine_links = create_query_engine(index, chat=False)
query_engine_transcripts = create_query_engine(index_transcripts, chat=False)

template = (
    "Your context is a list of urls for OpenShift commons videos. Each input has a url, and a title for the video \n"
    "indicating what the video was abput \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "You are a helpful AI assistant who can provide me which video is best matching to my query. \n"
    "give me the most relevant videos URLs from the context I gave you: {query_str}\n"
    "format reply for slack like this: Here are some relevant videos you might like: [Title](URL) \n"
    "If you don't have the URL, provide a link to a video that you think is VERY relevant to the query. \n"
)

template_transcripts = (
    "Your context is a list of youtube transcripts. Each transcript is for a video that talks about a certain topic \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "You are a helpful AI assistant who can pick the best information from the transcripts. \n"
    "give me the most relevant information from the best transcripts in the form of a paragraph. \n"
    "Share the URLs of the video you got the infromation from: {query_str}\n"
    "Make sure the response is formated nicely to be read on slack especially for lists. \n"
    "For Lists, use unordered lists. \n"
    "Make sure the URLs are correct and well formatted. \n"
    "If you don't have the URL, provide a link to a video that you think is VERY relevant to the query. \n"
)

agentContext = """
You are a youtube links and videos sorcerer who is an expert OpenShift commons and cloud-native technologies.\
You will answer questions about OpenShift and cloud-native topics in the persona of a sorcerer. \
You will give multiple links from the context and corpus you were provided, make sure the links are well formatted.\
If you don't have the URL, provide a link to a video that you think is VERY relevant to the query.\
Make sure the link you share and it's title match, don't send wrong links. \
if you don't find a link, provide a link to a video that you think is VERY relevant to the query. \
Use slack_tools to search for similar questions and provide the best answer. \
Use feed_tools to fetch news and updates about OpenShift, Kubernetes and cloud-native technologies. \
Make sure the response is formated nicely to be read on slack especially for lists. \
For Lists, use unordered lists. \
"""


# qa_template = PromptTemplate(template)   
qa_template_transcripts = PromptTemplate(template_transcripts)

# query_engine_links.update_prompts(
#         {"response_synthesizer:text_qa_template": qa_template}
# )
query_engine_transcripts.update_prompts(
        {"response_synthesizer:text_qa_template": qa_template_transcripts}
)

# Initializes your app with your bot token and signing secret
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
slack_tool_spec = SlackToolSpec(client=slack_client)
slack_tool = slack_tool_spec.to_tool_list()

feed_tool_spec = FeedSpec()
feed_tool = feed_tool_spec.to_tool_list()

query_engine_tools = [
    *slack_tool,
    *feed_tool,
    # QueryEngineTool(
    #     query_engine=query_engine_links,
    #     metadata=ToolMetadata(
    #         name="youtube_links",
    #         description="Links for OpenShift commons videos. Each input has a url, and a title for the video indicating what the video was about.",
    #     ),
    # ),
    QueryEngineTool(
        query_engine=query_engine_transcripts,
        metadata=ToolMetadata(
            name="youtube_transcripts",
            description="Transcripts for OpenShift commons videos. Each transcript is for a video that talks about a certain topic.",
        ),
    ),
]

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
*Here are more things you can do*

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
