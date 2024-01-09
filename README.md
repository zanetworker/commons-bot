# Commons-Bot

This is a GitHub project that includes code for a Slack app called `commons-bot`. The purpose of this app is to provide onboarding to new and existing users for the [openshift-commons community](https://join.slack.com/t/openshiftcommons/shared_invite/zt-2a9hn25ck-sY1Z86dEzMnysoU0te0hpA).

## Getting Started

To set up the commons-bot app, follow these steps:

1. Clone the GitHub repository to your local machine.
2. Make sure you have Python installed.
3. Install the required packages by running the following command:

   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project directory and add the following environment variables:

   ```
   SLACK_BOT_TOKEN=<your_slack_bot_token>
   SLACK_SIGNING_SECRET=<your_slack_signing_secret>
   ```

   Make sure to replace `<your_slack_bot_token>` and `<your_slack_signing_secret>` with your own Slack bot token and signing secret. You can obtain these by creating a Slack app in your Slack workspace.

5. Run the following command to start the Flask app:

   ```
   python app_http_mode.py
   ```

   The app will run locally on port 5002.

## Features

The common-bot app provides the following features:

### Team Join Event Handling

When a new member joins the team, the app can handle the `team_join` event. You can add your own logic for handling this event in the `handle_member_joined_channel` function.

### Message Event Handling

The app can handle incoming message events. You can customize the logic for handling message events in the `handle_message_events` function.

### Onboard Command Handling

The app handles the `/onboard` command, allowing users to provide information about their role or interests. This command triggers the `handle_onboard_command` function, which displays a list of roles and interests as buttons. When a user selects a role or interest, the app suggests specific Slack channels based on their selection.

### Role Selection Action Handling

The app handles the selection of a role or interest by users. When a user selects a role or interest button, the app suggests specific Slack channels related to that role. The role selection action is handled in the `handle_role_selection` function.

### Slack Event and Command Endpoints

The app provides the following Flask endpoints to handle Slack events and commands:

- `/slack/events` - Handles Slack events.
- `/slack/commands` - Handles Slack commands.

### Slack Interactive Endpoint

The app also provides a Flask endpoint `/slack/interactive` to handle interactive components within Slack. This enables the app to respond to user interactions, such as role selection, and suggest channels accordingly.
