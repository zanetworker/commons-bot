import os,re,json
import awsgi
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient, WebhookClient


client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])


# Initializes your app with your bot token and signing secret
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

# Flask app to handle requests
flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)

# Event, command, and action handlers
@slack_app.event("team_join")
def handle_member_joined_channel(event, client):
    # Your existing code for handling team_join event
    pass 

@slack_app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

# Handling '/onboard' command
@slack_app.command("/onboard")
def handle_onboard_command(ack, body, say):
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

# ... [your existing Flask app code] ...

def handler(event, context):
    return awsgi.response(flask_app, event, context)
