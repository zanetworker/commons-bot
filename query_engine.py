import os
from slack_sdk import WebClient
from llama_index.postprocessor.colbert_rerank.base import ColbertRerank

from llama_index.core import PromptTemplate
from llama_index.core.tools import QueryEngineTool, ToolMetadata

from tool_specs import SlackToolSpec, FeedSpec
from memory_profiler import profile


class QueryEngineManager:
    # __slots__ = ['index', 'templates', '_agent_context']

    # @profile
    def __init__(self, index):
        self.index = index
        self.templates = {
            'links': (
                "Your context is a list of urls for OpenShift commons videos. Each input has a url, and a title for the video \n"
                "indicating what the video was about \n"
                "---------------------\n"
                "{context_str}"
                "\n---------------------\n"
                "You are a helpful AI assistant who can provide me which video is best matching to my query. \n"
                "give me the most relevant videos URLs from the context I gave you: {query_str}\n"
                "format reply for slack like this: Here are some relevant videos you might like: [Title](URL) \n"
                "If you don't have the URL, provide a link to a video that you think is VERY relevant to the query. \n"
            ),
            # 'transcripts': (
            #     "Begin by examining the YouTube video transcripts provided, each focusing on a specific topic. \n"
            #     "1. Read each transcript to understand the topics discussed, aiding in identifying the most relevant information to the query. \n"
            #     "2. Select the transcripts that are most informative and relevant to the query, based on their depth, clarity, and relevance. \n"
            #     "3. Synthesize the key points from these transcripts into a coherent paragraph, distilling the essence of the information. \n"
            #     "4. List the *full* URLs of the source videos, ensuring accuracy for traceability. If a URL is missing, provide a highly relevant alternative. \n"
            #     "5. Format your response to be clear and structured for easy reading. Begin with an introductory sentence, followed by the synthesized paragraph, and end with a section titled 'Source Videos' where you list the URLs as bullet points. \n"
            #     "This structured approach ensures the response is organized, accessible, and easily interpretable. \n"
            #     "---------------------\n"
            #     "{context_str}"
            #     "\n---------------------\n"            
            #     "Your task is to follow these steps meticulously to provide a well-structured and informative response based on the transcripts. "
            #     "\n\n"
            # )
            'transcripts': (
                "Your context is a list of youtube transcripts. Each transcript is for a video that talks about a certain topic \n"
                "---------------------\n"
                "{context_str}"
                "\n---------------------\n"
                "You are a helpful AI assistant who can pick the best information from the transcripts. \n"
                "give me the most relevant information from the best transcripts in the form of a paragraph. \n"
                "Share the URLs of the video you got the information from: {query_str}\n"
                "Make sure the response is formatted nicely to be read on slack especially for lists. \n"
                "For Lists, use unordered lists. \n"
                "Make sure the URLs are correct and well formatted. \n"
                "If you don't have the URL, provide a link to a video that you think is VERY relevant to the query. \n"
            )
        }
    #     self._agent_context = (
    #         "You embody the essence of a sorcerer, specializing in the mystical domain "
    #         "of YouTube transcripts, links, and videos, deeply versed in OpenShift commons, kubernetes, and "
    #         "cloud-native technologies. Your mission is to dispense wisdom in the "
    #         "manner of a cloud-native expert sorcerer, enriching queries with insights on OpenShift and "
    #         "cloud-native realms. Your arsenal includes a vast collection of links and transcripts; "
    #         "ensure these are accurately conjured and lead to the knowledge realms "
    #         "they profess. In the absence of a direct link in your tome, say that is beyond your knowledge"
    #         "It is imperative to verify the harmony between the title and the link's essence, "
    #         "as a sorcerer's path is one of integrity, not deceit. When ancient scrolls fall "
    #         "short, turn to the `slack_tools` oracle for akin mysteries and their resolutions, "
    #         "and invoke the `feed_tools` spirits for the latest chronicles in OpenShift, Kubernetes, "
    #         "and cloud-native lore. Craft your revelations in a manner that beholds the eye within "
    #         "Slack domains, using the language of the stars (*) to embolden your script, as the "
    #         "double stars (**) are not of our customs."
    # )
        self._agent_context = (
            "You are a youtube links and videos sorcerer who is an expert OpenShift commons and cloud-native technologies."
            "You will answer questions about OpenShift and cloud-native topics in the persona of a sorcerer."
            "You will give multiple links from the context and corpus you were provided, make sure the links are well formatted. "
            "If you don't have the URL, provide a link to a video that you think is VERY relevant to the query. "
            "Make sure the link you share and it's title match, don't send wrong links. "
            "Make sure to add relevant context and mention how you got the information."
            "if you don't find a link, provide a link to a video that you think is VERY relevant to the query."
            "Use slack_tools to search for similar questions and provide the best answer."
            "Use feed_tools to fetch news and updates about OpenShift, Kubernetes and cloud-native technologies."
            "Make sure the response is formated nicely to be read on slack especially for lists."
            "Make sure to use single asterisk (*) for bold text don't use (**)."
        )


    def _update_prompts(self, query_engine):
        # Assuming 'transcripts' is the key for the transcripts template
        transcripts_template = self._get_template('transcripts')
        qa_template_transcripts = PromptTemplate(transcripts_template)
        query_engine.update_prompts({"response_synthesizer:text_qa_template": qa_template_transcripts})

    def _get_template(self, key):
        return self.templates.get(key, "")

    def get_agent_context(self):
        return self._agent_context
    
    def create_query_engine(self, similarity_top_k=5, streaming=True, chat=False, rerank=False):
        if rerank:
            colbert_reranker = ColbertRerank(
                top_n=5,
                model="colbert-ir/colbertv2.0",
                tokenizer="colbert-ir/colbertv2.0",
                keep_retrieval_score=True,
            )

            query_engine = self.index.as_chat_engine(streaming=streaming, similarity_top_k=similarity_top_k, node_postprocessors=[colbert_reranker]) if chat else self.index.as_query_engine(similarity_top_k=similarity_top_k, streaming=streaming, node_postprocessors=[colbert_reranker])
        else:
            query_engine = self.index.as_chat_engine(streaming=streaming, similarity_top_k=similarity_top_k) if chat else self.index.as_query_engine(similarity_top_k=similarity_top_k, streaming=streaming)
        
        self._update_prompts(query_engine)
        return query_engine


class QueryEngineToolsManager:
    # add __slots__ to reduce memory usage
    # __slots__ = ['_slack_tool_spec', '_feed_tool_spec', '_query_engine']
    # @profile
    def __init__(self, query_engine):
        self._slack_tool_spec = SlackToolSpec(client=WebClient(token=os.environ["SLACK_BOT_TOKEN"]))
        self._feed_tool_spec = FeedSpec()
        self._query_engine = query_engine

    @property
    def slack_tool(self):
        return self._slack_tool_spec.to_tool_list()

    @property
    def feed_tool(self):
        return self._feed_tool_spec.to_tool_list()

    @property
    def query_engine_tools(self):
        # Assuming metadata and other necessary configurations for the query engine tools are set correctly
        youtube_transcripts_tool = QueryEngineTool(
            query_engine=self._query_engine,
            metadata=ToolMetadata(
                name="youtube_transcripts",
                description="Transcripts for OpenShift commons videos. Each transcript is for a video that talks about a certain topic.",
            ),
        )
        return [*self.slack_tool, *self.feed_tool, youtube_transcripts_tool]
