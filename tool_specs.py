from typing import List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from llama_index.tools.tool_spec.base import BaseToolSpec


from dotenv import load_dotenv
load_dotenv()


class SlackToolSpec(BaseToolSpec):
    """Slack tool spec."""
    spec_functions = ["get_channel_history_by_query"]

    def __init__(self, client: WebClient):
        self.client = client

    def search_messages(self, query: str) -> List[dict]:
        """Search for messages matching a query."""
        try:
            result = self.client.search_messages(query=query)
            if result['ok']:
                return result['messages']['matches']
            else:
                print("Search unsuccessful:", result['error'])
                return []
        except SlackApiError as e:
            print(f"Error searching messages: {e.response['error']}")
            return []

    def get_channel_history(self, channel_id: str, limit: int = 100) -> List[dict]:
        """Fetches the message history of a channel."""
        try:
            response = self.client.conversations_history(channel=channel_id, limit=limit)
            if response["ok"]:
                return response["messages"]
            else:
                print(f"Error fetching channel history: {response['error']}")
                return []
        except SlackApiError as e:
            print(f"Slack API Error: {e.response['error']}")
            return []
                
    def get_channel_history_by_query(self, query: str, limit: int = 100) -> List[dict]:
        """Fetches channel history and filters messages by a search query."""
        messages = self.get_channel_history("C0FNVPMNF", limit)
        query_related_messages = []

        for message in messages:
            # Check if the query is in the message text
            if query.lower() in message.get('text', '').lower():
                query_related_messages.append(message)

        return query_related_messages