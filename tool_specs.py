import logging
from typing import List, Optional
from llama_index.core.tools.tool_spec.base import BaseToolSpec
from slack_sdk.errors import SlackApiError

from memory_profiler import profile

from dotenv import load_dotenv

load_dotenv()

# add logs
logging.basicConfig(level=logging.INFO)

class SlackToolSpec(BaseToolSpec):
    from slack_sdk import WebClient

    """Slack tool spec."""
    spec_functions = ["get_channel_history_by_query"]

    __slots__ = ['client']

    # @profile
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

        # fixed to general channel for now
        # TODO - make this more dynamic
        _general_channel = "C0FNVPMNF"
        messages = self.get_channel_history(_general_channel, limit)
        query_related_messages = []

        for message in messages:
            # Check if the query is in the message text
            if query.lower() in message.get('text', '').lower():
                query_related_messages.append(message)

        return query_related_messages


# build a spec to check if youtube url is functional
class YoutubeSpec(BaseToolSpec):
    """Youtube tool spec."""
    spec_functions = ["check_youtube_url"]

    def check_youtube_url(self, url) -> str:
        """Check if the youtube url is functional."""
        from pytube import YouTube
        valid_yt_links = []
        try:
            yt = YouTube(url)
            yt.check_availability()
            return "Valid youtube link"
        except Exception as e:
            print(f"Error checking youtube link {url}: {e}")
            # return exception message
            return str(e)


class FeedSpec(BaseToolSpec):
    """News fetcher specification."""
    spec_functions = ["fetch_news"]

    __slots__ = ['feed_urls']

    # @profile
    def __init__(self):
        self.feed_urls = [
            "https://www.cncf.io/rss",
            "https://kubernetes.io/feed.xml",
            "https://www.redhat.com/en/rss/blog",
            "https://research.redhat.com/feed/"
        ]

    def fetch_news(self) -> str:
        import feedparser

        """Fetch news items from specified feeds."""
        print("Fetching news...")
        formatted_news_list = []
        for url in self.feed_urls:
            try:
                # Parse the feed
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    formatted_item = f"Title: {entry.title}\n" \
                                     f"Link: {entry.link}\n" \
                                     f"Published: {entry.published}\n" \
                        # f"Summary: {entry.summary}\n" \
                    formatted_news_list.append(formatted_item)

            except Exception as e:
                # log error
                logging.error(f"Error parsing RSS URL '{url}': {e}")
                # print(f"Error fetching news from {url}: {e}")

        # limit items in formatted_news_list that contain openshift or red hat to 4 and include the rest up to 10
        red_hat_openshift_news = [news for news in formatted_news_list if
                                  "red hat" in news.lower() or "openshift" in news.lower()]

        formatted_news_list = [news for news in formatted_news_list if news not in red_hat_openshift_news]
        formatted_news_list = red_hat_openshift_news[:4] + formatted_news_list
        formatted_news_list = formatted_news_list[:10]

        print("\n\n".join(formatted_news_list))
        return "\n\n".join(formatted_news_list)


class BingSearchToolSpec(BaseToolSpec):
    """Bing Search tool spec."""

    spec_functions = ["bing_search", "bing_news_search", "bing_video_search"]
    # spec_functions = ["bing_news_search", "bing_image_search", "bing_video_search"]

    def __init__(
            self, api_key: str, lang: Optional[str] = "en-US", results: Optional[int] = 5
    ) -> None:
        """Initialize with parameters."""
        self.api_key = api_key
        self.lang = lang
        self.results = results

    def _bing_request(self, endpoint: str, query: str, keys: List[str], freshness: str = "Year"):
        import requests
        import logging

        # Log
        logging.info(f"Making a request to Bing {endpoint} with query: {query}")

        # Endpoint base URL
        endpoint_base_url = "https://api.bing.microsoft.com/v7.0/"

        # Making the request
        response = requests.get(
            endpoint_base_url + endpoint,
            headers={"Ocp-Apim-Subscription-Key": self.api_key},
            params={
                "q": query,
                "mkt": self.lang,
                "count": self.results,
                "freshness": freshness,  # Use the freshness parameter here
            },
        )

        # Processing the response
        response_json = response.json()
        print(response)

        # Extracting and returning the desired information from the results
        return [[result[key] for key in keys] for result in response_json.get("value", [])]

    # write a function to do bing search
    def bing_search(self, query: str):
        """
        Make a query to bing news search. Useful for finding news on a query.

        Args:
            query (str): The query to be passed to bing.

        """
        return self._bing_request("search", query, ["name", "description", "url"])

    def bing_news_search(self, query: str):
        """
        Make a query to bing news search. Useful for finding news on a query.

        Args:
            query (str): The query to be passed to bing.

        """
        return self._bing_request("news/search", query, ["name", "description", "url"])


    def bing_image_search(self, query: str):
        """
        Make a query to bing images search. Useful for finding an image of a query.

        Args:
            query (str): The query to be passed to bing.

        returns a url of the images found
        """
        return self._bing_request("images/search", query, ["name", "contentUrl"])

    def bing_video_search(self, query: str):
        """
        Make a query to bing video search. Useful for finding a video related to a query.

        Args:
            query (str): The query to be passed to bing.

        """
        return self._bing_request("videos/search", query, ["name", "contentUrl"])
