from typing import List


class EmbeddingModel:

    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed(self, texts: List[str]) -> list[list[float]]:
        self._load_model()
        return self._model.encode(texts).tolist()    