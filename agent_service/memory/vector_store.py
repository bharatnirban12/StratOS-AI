import os
import uuid
from chromadb import Client
from chromadb.config import Settings
from agent_service.memory.embedding import EmbeddingModel

class VectorStore:
    _client = None
    _collection = None

    def __init__(self):
        if VectorStore._client is None:
            VectorStore._client = Client(Settings(anonymized_telemetry=False))
            VectorStore._collection = VectorStore._client.get_or_create_collection(
                name="agent_memory"
            )
        
        self.client = VectorStore._client
        self.collection = VectorStore._collection
        self.embedding_model = EmbeddingModel()

    def add(self, simulation_id: str, content: str):
        
        if os.getenv("TEST_MODE") == "true":
            return
        
        
        if not simulation_id:
            simulation_id = "unknown"

        content = str(content)    
        embedding = self.embedding_model.embed([content])[0]
        
        
        self.collection.add(
            documents = [content],
            embeddings = [embedding],
            metadatas=[{"simulation_id" : simulation_id}],
            ids = [f"{simulation_id}_{uuid.uuid4()}"]
        )    

    def search(self, simulation_id: str, query: str, k: int = 3):
        
        if os.getenv("TEST_MODE") == "true":
            return []
        
        query_embedding = self.embedding_model.embed([query])[0]
        
        results = self.collection.query(
            query_embeddings =[query_embedding],
            n_results=k,
            where={"simulation_id": simulation_id}
        )
        
        documents = results.get("documents", [])

        if documents and isinstance(documents[0], list):
            return documents[0]

        return documents    

         