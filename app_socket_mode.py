import os, re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from slack_sdk import WebClient

# Load environment variables from .env file
load_dotenv()

# Initializes your app with your bot token and signing secret
app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

# print envs 

print("Environment variables:")
print(os.environ["SLACK_BOT_TOKEN"])
print(os.environ["SLACK_SIGNING_SECRET"])
print(os.environ["SLACK_APP_TOKEN"])



@app.event("team_join")
def handle_member_joined_channel(event, client):
    user_id = event['user']
    channel_id = event['channel']

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
    # Send a welcome message to the new member if their role or interest is listed above
    user_info = client.users_info(user=user_id)
    user_name = user_info['user']['real_name']

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

    client.chat_postMessage(channel=channel_id, blocks=blocks, text=f"Welcome <@{user_id}>")    

@app.command("/onboard")
def handle_some_command(ack, body, say):
    ack()
    user_id = body["user_id"]
    channel_id = body["channel_id"]

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
    response = {
        "blocks": blocks,  # 'blocks' as defined in your existing code
        "text": f"Welcome <@{user_id}>",
        "channel": channel_id
    }
    say(blocks=blocks, text=f"Welcome <@{user_id}>", channel=channel_id)


# Initialize a Web client with your bot token
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

@app.action(re.compile("select_(.*)"))
def handle_role_selection(ack, body, say):
    ack()
    action_id = body['actions'][0]['action_id']
    role = action_id.split('select_')[1].replace('_', ' ').lower()

    user_id = body["user"]["id"]
    # Suggested channels based on the role or interests
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

    channel_names_id = channel_suggestions.get(role, [])

    suggested_channels = [{"name": name_id['name'], "id": name_id['id']} for name_id in channel_names_id]   
    print(suggested_channels) 
    # Filter out any channels where the ID couldn't be found
    suggested_channels = [channel for channel in suggested_channels if channel['id'] is not None]

    # Format the message with clickable channel links
    suggested_channels_text = "\n".join([f"- <#{channel['id']}|{channel['name']}>" for channel in suggested_channels])

    say(
        text=f"<@{user_id}> based on your interest in {role}, we suggest you join the following channels:\n{suggested_channels_text}"
    )


# Cache for channel IDs
channel_id_cache = {}
def update_channel_id_cache():
    try:
        # Call the conversations.list method using the WebClient
        for response in client.conversations_list(limit=1000):
            channels = response['channels']
           
            for channel in channels:
                # Cache the channel ID with the channel name as the key
                channel_id_cache[channel['name']] = channel['id']
                # print(channel['name'], channel['id'])
    except SlackApiError as e:
        print(f"Error fetching conversations: {e}")


def get_channel_id_by_name(channel_name):
    # Use the cached ID if available
    print(channel_name)
    print(channel_id_cache.get(channel_name))
    return channel_id_cache.get(channel_name)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()