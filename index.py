from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore

from qdrant_client.http import models
from memory_profiler import profile

class IndexManager:
    # @profile
    def __init__(self, qd_client, service_context, collection_name="commons"):
        self.qd_client = qd_client
        self.collection = collection_name
        self.service_context = service_context

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

            # openai uses 1536 embedding sizes
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )

    def create_or_load_index(self, youtube_transcripts=None):
        collection_exists = self._check_collection_exists()

        vector_store = QdrantVectorStore(client=self.qd_client, collection_name=self.collection, service_context=self.service_context)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        if not collection_exists and youtube_transcripts is not None:
            print("Collection does not exist, creating new index from documents")
            return VectorStoreIndex.from_documents(documents=youtube_transcripts, storage_context=storage_context, service_context=self.service_context)
        else:
            print("Collection exists, loading index from storage")
            return VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context, service_context=self.service_context)


