from memory_profiler import profile

# import and use logging 
import logging
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class IndexManager:
    # __slots__ = ['qd_client', 'collection', 'service_context']

    # @profile
    def __init__(self, qd_client, service_context, embed_model, collection_name="commons"):
        self.qd_client = qd_client
        self.collection_name = collection_name
        self.service_context = service_context
        self.embed_model = embed_model
        self.documents = None

    def _check_collection_exists(self):
        try:
            return True if self.qd_client.get_collection(collection_name=self.collection_name) else False
        except Exception as e:
            # print error message
            # self._create_collection()
            print(e)
            return False

    def _create_collection(self):
        from qdrant_client.http import models

        self.qd_client.create_collection(
            collection_name=self.collection_name,

            # openai uses 1536 embedding sizes
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )

    def create_or_load_index(self):
        from llama_index.core.indices.vector_store import VectorStoreIndex
        from llama_index.core.storage import StorageContext
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        # from llama_index.legacy.vector_stores.qdrant import QdrantVectorStore
        
        collection_exists = self._check_collection_exists()

        vector_store = QdrantVectorStore(collection_name=self.collection_name, client=self.qd_client, service_context=self.service_context)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        if not collection_exists:
            from loaders import YouTubeLoader

            youtube_loader = YouTubeLoader()
            youtube_transcripts = youtube_loader.yttranscripts
            
            # define splitter. Optimize params (chunk size and overlap for pure text splitters, otherwise special
            # params e.g., for semantic splitters)
            # node_parser = SemanticSplitterNodeParser(
            #     buffer_size=1, breakpoint_percentile_threshold=95, embed_model=self.embed_model
            # )
            # base_nodes = node_parser.get_nodes_from_documents(documents=youtube_transcripts, show_progress=True)

            print("Collection does not exist, creating new index from documents")
            return VectorStoreIndex.from_documents(documents=youtube_transcripts, storage_context=storage_context, service_context=self.service_context, show_progress=True)

        else:
            print("Collection exists, loading index from storage")
            return VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context, service_context=self.service_context)

    def retriever(self, index):
        # find top 2 nodes
        base_retriever = index.as_retriever(similarity_top_k=5)

        retrievals = base_retriever.retrieve(
            "what is k-native?"
        )

        for n in retrievals:
            print(n)


    def splitter(self, documents):

        # evaluate embeddings with
        from llama_index.core.node_parser import (
            SentenceSplitter,
            SemanticSplitterNodeParser,
            MetadataAwareTextSplitter,
            )

        # semantic chunking does not work well for youtube transcripts
        # splitter = SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=95, embed_model=self.embed_model)
        # # nodes_semantic = splitter.get_nodes_from_documents(documents=documents)

        # also baseline splitter
        # https://neo4j.com/developer-blog/youtube-transcripts-knowledge-graphs-rag/ 
        base_splitter = SemanticSplitterNodeParser(
            buffer_size=1, breakpoint_percentile_threshold=95, embed_model=self.embed_model
        )
        # base_splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=64)
        nodes_base= base_splitter.get_nodes_from_documents(documents, show_progress=True)

        # print len of nodes_base
        print(len(nodes_base))
        # # print the first three nodes
        # print(nodes_semantic[0])
        # print(nodes_semantic[1])
        # print(nodes_semantic[2])

        # print("-----------------")
        # print(nodes_base[0])
        # print(nodes_base[1])
        # print(nodes_base[2])
