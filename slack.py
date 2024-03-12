from llama_index.core.agent.react import ReActAgent
from llama_index.core import Settings

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


class SlackOperations:
    def __init__(self, app):
        self.app = app

    def post_ephemeral_message(self, channel, user, text, message_blocks=None, thread_ts=None):
        self.app.client.chat_postEphemeral(
            channel=channel,
            user=user,
            text=text,
            blocks=message_blocks,
            thread_ts=thread_ts
        )

    def post_message(self, channel, text, thread_ts=None, blocks=None):
        self.app.client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts,
            blocks=blocks
        )

    def add_reaction(self, channel, timestamp, emoji):
        self.app.client.reactions_add(
            name=emoji,
            channel=channel,
            timestamp=timestamp
        )

    def remove_reaction(self, channel, timestamp, emoji):
        self.app.client.reactions_remove(
            name=emoji,
            channel=channel,
            timestamp=timestamp
        )

    def join_channel(self, channel_name):
        channel_list = self.app.client.conversations_list().data
        channel = next((ch for ch in channel_list.get('channels', []) if ch.get("name") == channel_name), None)
        if channel:
            channel_id = channel.get('id')
            self.app.client.conversations_join(channel=channel_id)
            return channel_id
        return None

    # Additional methods for other operations like posting messages, adding reactions, etc.


# Other imports as needed

class CommandHandler:
    def __init__(self, slack_ops: SlackOperations, query_engine_transcripts, query_engine_agent_commands_tools,
                 agent_commands_context):
        self.slack_ops = slack_ops
        self.query_engine_transcripts = query_engine_transcripts
        self.query_engine_agent_commands_tools = query_engine_agent_commands_tools
        self.agent_commands_context = agent_commands_context

    def process_command_query_with_retry(self, process_func, channel_id, user_id, thread_ts=None):
        max_attempts = 5
        try_count = 0
        for attempt in range(max_attempts):
            try:
                response = process_func()
                formatted_transcripts_response = utils.convert_to_slack_formatting(str(response))

                self.slack_ops.post_ephemeral_message(channel_id, user_id, formatted_transcripts_response, thread_ts)

                return True
            except Exception as e:
                print(f"Error: {str(e)}")
                try_count += 1

        if try_count == max_attempts:
            self.slack_ops.post_ephemeral_message(channel_id, user_id,
                                                  "No further information to provide.",
                                                  thread_ts)
        return False


    def handle_commons_command_agent_only(self, ack, command):
        ack()
        user_id = command['user_id']
        channel_id = command['channel_id']
        query = command['text']

        self.slack_ops.post_ephemeral_message(channel_id, user_id,
                                              "Got your command, working on it! :hourglass_flowing_sand:")

        self.process_command_query_with_retry(
            lambda: ReActAgent.from_tools(
                self.query_engine_agent_commands_tools,
                llm=Settings.llm,
                verbose=True,
                context=self.agent_commands_context).chat(query),
            channel_id, user_id
        )
    def handle_commons_command(self, ack, command):
        ack()
        user_id = command['user_id']
        channel_id = command['channel_id']
        query = command['text']

        self.slack_ops.post_ephemeral_message(channel_id, user_id,
                                              "Got your command, working on it! :hourglass_flowing_sand:")

        transcripts_processed = self.process_command_query_with_retry(
            lambda: self.query_engine_transcripts.query(query),
            channel_id,
            user_id,
        )

        if transcripts_processed:
            self.slack_ops.post_ephemeral_message(channel_id, user_id,
                                                  "Getting you more information :information_source:")

            self.process_command_query_with_retry(
                lambda: ReActAgent.from_tools(
                    self.query_engine_agent_commands_tools,
                    llm=Settings.llm,
                    verbose=True,
                    context=self.agent_commands_context).chat(query),
                channel_id, user_id
            )

    def handle_onboard_command(self, ack, body, client):
        ack()

        user_id = body["user_id"]
        onboard_channel_id = body["channel_id"]
        thread_ts = body.get('thread_ts', None)  # Get thread_ts if present

        self.slack_ops.post_ephemeral_message(
            channel=onboard_channel_id,
            user=user_id,
            text=f"Welcome <@{user_id}>",
            message_blocks=blocks,
            thread_ts=thread_ts
        )

    def handle_help_command(self, ack, body, client):
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

        self.slack_ops.post_ephemeral_message(channel_id, user_id, help_message)

    # Other command handlers as methods of this class


import utils


class MessageHandler:
    def __init__(self, slack_ops: SlackOperations, query_engine_transcripts, query_engine_agent_commands_tools,
                 agent_commands_context):
        self.slack_ops = slack_ops
        self.query_engine_transcripts = query_engine_transcripts
        self.query_engine_agent_commands_tools = query_engine_agent_commands_tools
        self.agent_commands_context = agent_commands_context

    def process_message_query_with_retry(self, process_func, channel_id, user_id, thread_ts=None):
        max_attempts = 7

        try_count = 0
        for attempt in range(max_attempts):
            try:
                response = process_func()
                formatted_response = utils.convert_to_slack_formatting(str(response))
                self.slack_ops.post_message(channel_id, formatted_response, thread_ts=thread_ts)
                return True
            except Exception as e:
                print(f"Error: {str(e)}")
                try_count += 1

        if try_count == max_attempts:
            self.slack_ops.post_message(
                channel_id,
                "No further information to provide.",
                thread_ts=thread_ts
            )

        return False

    def process_message_query_agent_only(self, query, reply_channel_id, reply_user_id, thread_ts):
        self.slack_ops.add_reaction(reply_channel_id, thread_ts, "hourglass_flowing_sand")

        self.slack_ops.post_ephemeral_message(
            reply_channel_id,
            reply_user_id,
            text="Got your command, working on it! :hourglass_flowing_sand:"
        )

        self.process_message_query_with_retry(
            lambda: ReActAgent.from_tools(
                self.query_engine_agent_commands_tools,
                llm=Settings.llm,
                verbose=True,
                context=self.agent_commands_context).chat(query),
            channel_id=reply_channel_id,
            user_id=reply_user_id,
            thread_ts=thread_ts
        )

        # remove the hourglass emoji and add a checkmark
        self.slack_ops.remove_reaction(reply_channel_id, thread_ts, "hourglass_flowing_sand")
        self.slack_ops.add_reaction(reply_channel_id, thread_ts, "white_check_mark")


    def process_message_query(self, query, reply_channel_id, reply_user_id, thread_ts):
        self.slack_ops.add_reaction(reply_channel_id, thread_ts, "hourglass_flowing_sand")

        self.slack_ops.post_ephemeral_message(
            reply_channel_id,
            reply_user_id,
            text="Got your command, working on it! :hourglass_flowing_sand:"
        )

        transcripts_processed = self.process_message_query_with_retry(
            lambda: self.query_engine_transcripts.query(query),
            reply_channel_id,
            reply_user_id,
            thread_ts
        )

        if transcripts_processed:
            self.slack_ops.post_ephemeral_message(reply_channel_id, reply_user_id,
                                                  "Getting you more information :information_source:")

            self.process_message_query_with_retry(
                lambda: ReActAgent.from_tools(
                    self.query_engine_agent_commands_tools,
                    llm=Settings.llm,
                    verbose=True,
                    context=self.agent_commands_context).chat(query),
                channel_id=reply_channel_id,
                user_id=reply_user_id,
                thread_ts=thread_ts
            )

        # remove the hourglass emoji and add a checkmark
        self.slack_ops.remove_reaction(reply_channel_id, thread_ts, "hourglass_flowing_sand")
        self.slack_ops.add_reaction(reply_channel_id, thread_ts, "white_check_mark")

    def reply(self, message, bot_user_id):
        user_id = message['user']
        channel_id = message['channel']
        thread_ts = message.get('thread_ts', message['ts'])
        reply_blocks = message.get('blocks')

        if reply_blocks:
            for block in reply_blocks:
                if block.get('type') != 'rich_text':
                    print("TYPE IS:" + block.get('type'))
                    continue
                for rich_text_section in block.get('elements', []):
                    elements = rich_text_section.get('elements', [])
                    if any(element.get('type') == 'user' and element.get('user_id') == bot_user_id for element in
                           elements):
                        for element in elements:
                            if element.get('type') == 'text':
                                query = element.get('text')
                                self.process_message_query_agent_only(query, channel_id, user_id, thread_ts)

    def handle_message(self, message, say, client, bot_user_id):
        self.reply(message, bot_user_id)
