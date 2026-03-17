# app/infrastructure/ai/embeddings_model.py

# Componente de infraestructura encargado de convertir texto en embeddings
# usando un modelo SentenceTransformer. Estos vectores se utilizan luego en
# búsquedas semánticas, RAG y recuperación de contexto dentro del sistema.

import numpy as np
from sentence_transformers import SentenceTransformer

class EmbeddingsModel:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        # Carga el modelo preentrenado de embeddings que se usará en todo el sistema
        # para representar texto como vectores semánticos.
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        # Genera un embedding normalizado del texto y lo devuelve como lista de floats
        # para que pueda ser enviado fácilmente a la base de datos o a funciones RPC.
        vec = self.model.encode([text], normalize_embeddings=True)[0]
        return np.array(vec, dtype=np.float32).tolist()
