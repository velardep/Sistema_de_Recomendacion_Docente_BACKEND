import numpy as np
from sentence_transformers import SentenceTransformer

class EmbeddingsModel:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        # normalize_embeddings=True => mejora cosine similarity
        vec = self.model.encode([text], normalize_embeddings=True)[0]
        return np.array(vec, dtype=np.float32).tolist()
