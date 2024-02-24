from llama_index import VectorStoreIndex, ServiceContext, StorageContext
from llama_index.vector_stores import QdrantVectorStore
from qdrant_client.http import models

class IndexManager:
    def __init__(self, qd_client, llm):
        self.qd_client = qd_client
        self.collection = "commons"
        self.service_context = ServiceContext.from_defaults(llm=llm)

    def _check_collection_exists(self):
        try:
            self.qd_client.get_collection(collection_name=self.collection)
            return True
        except:
            self._create_collection()
            return False

    def _create_collection(self):
        self.qd_client.create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )

    def create_or_load_index(self, youtube_transcripts=None):
        collection_exists = self._check_collection_exists()

        vector_store = QdrantVectorStore(client=self.qd_client, collection_name=self.collection, service_context=self.service_context)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        if not collection_exists and youtube_transcripts is not None:
            return VectorStoreIndex.from_documents(documents=youtube_transcripts, storage_context=storage_context, service_context=self.service_context)
        else:
            print("Collection exists, loading index from storage")
            return VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context, service_context=self.service_context)


