import logging
from typing import List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from llama_index.core.tools.tool_spec.base import BaseToolSpec
import feedparser

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



class FeedSpec(BaseToolSpec):
    """News fetcher specification."""
    spec_functions = ["fetch_news"]


    def __init__(self):
        self.feed_urls = [
        "https://www.cncf.io/rss",
        "https://kubernetes.io/feed.xml",
        "https://www.redhat.com/en/rss/blog",
        "https://research.redhat.com/feed/"
    ]

    def fetch_news(self) -> str:
        """Fetch news items from specified feeds."""
        print("Fetching news...")
        formatted_news_list = []
        for url in self.feed_urls:
            try:
                # Parse the feed
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    formatted_item = f"Title: {entry.title}\n" \
                                    f"Link: { entry.link}\n" \
                                    f"Published: {entry.published}\n" \
                                    # f"Summary: {entry.summary}\n" \
                    formatted_news_list.append(formatted_item)
    
            except Exception as e:
                # log error
                logging.error(f"Error parsing RSS URL '{url}': {e}")
                # print(f"Error fetching news from {url}: {e}")
        
    

        # limit items in formatted_news_list that contain openshift or red hat to 4 and include the rest up to 10
        red_hat_openshift_news = [news for news in formatted_news_list if "red hat" in news.lower() or "openshift" in news.lower()]

        formatted_news_list = [news for news in formatted_news_list if news not in red_hat_openshift_news]
        formatted_news_list = red_hat_openshift_news[:4] + formatted_news_list
        formatted_news_list = formatted_news_list[:10]

        print("\n\n".join(formatted_news_list))
        return "\n\n".join(formatted_news_list)
