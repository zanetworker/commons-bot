# Commons-Bot

This is a GitHub project that includes code for a Slack app called `commons-bot`. The purpose of this app is to provide onboarding to new and existing users for the [openshift-commons community](https://join.slack.com/t/openshiftcommons/shared_invite/zt-2a9hn25ck-sY1Z86dEzMnysoU0te0hpA).

## Getting Started

To set up the commons-bot app, follow these steps:

1. Clone the GitHub repository to your local machine.
2. Make sure you have Python installed.
3. Install the required packages by running the following command (use pip or poetry):

   ```shell
   pip install -r requirements.txt

   # or poetry
   poetry install 
   ```

4. Create a `.env` file in the project directory and add the following environment variables:

   ```shell
   SLACK_BOT_TOKEN=<your_slack_bot_token>
   SLACK_SIGNING_SECRET=<your_slack_signing_secret>
   GRAPH_SIGNAL_API_KEY=<key>
   OPENAI_API_KEY=<key>
   QD_API_KEY=<api_key>
   QD_ENDPOINT=<endpoint>
   ```

   Make sure to replace `<your_slack_bot_token>` and `<your_slack_signing_secret>` with your own Slack bot token and signing secret. You can obtain these by creating a Slack app in your Slack workspace.

5. Run the following command to start the Flask app:

   ```shell
   python commons-bot.py
   ```

   The app will run locally on port 5002.

## Features

The common-bot app provides the following features:

### Team Join Event Handling

When a new member joins the team, the app can handle the `team_join` event. You can add your own logic for handling this event in the `handle_member_joined_channel` function.

### Message Event Handling

The app can handle incoming message events. You can customize the logic for handling message events in the `handle_message_events` function.

### Command Handling

The app handles the `/onboard`, `/commons`, and `/help` commands to handle onboarding as well as question answering from corpus.

### Slack Interactive Endpoint

The app also provides a Flask endpoint `/slack/interactive` to handle interactive components within Slack. This enables the app to respond to user interactions, such as role selection, and suggest channels accordingly.

## Evaluation

The following are the results of the evaluation, with chunk size `1024` achieving highest average faithfulness and average relevancy.

| Chunk Size | Average Response Time (s) | Average Faithfulness | Average Relevancy |
|------------|---------------------------|----------------------|-------------------|
| 128        | 12.33                     | 0.90                 | 0.88              |
| 256        | 11.35                     | 0.95                 | 0.93              |
| 512        | 11.56                     | 0.85                 | 0.85              |
| 1024       | 12.24                     | 0.97                 | 0.95              |
| 2048       | 11.74                     | 0.93                 | 0.90              |
