from abc import ABC, abstractmethod
from typing import List


class LLMClient(ABC):

    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        context_chunks: List[str],
        history: List[dict],
    ) -> str:
        """
        Genera una respuesta final usando:
        - prompt principal
        - contexto semántico (RAG)
        - historial del chat
        """
        pass
