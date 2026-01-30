# app/infrastructure/llm/gemini_client.py
from google import genai
from google.genai import types
from app.domain.ports.outbound.llm_client import LLMClient
from app.infrastructure.config.settings import settings
import asyncio


class GeminiClient(LLMClient):
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Tool oficial de grounding con Google Search (Gemini decide cuándo usarlo)
        # https://ai.google.dev/gemini-api/docs/google-search
        self.grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

    async def generate(
        self,
        *,
        prompt: str,
        context_chunks: list[str],
        history: list[dict],
    ) -> str:
        contexto = "\n".join(f"- {c}" for c in (context_chunks or []))

        historial = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in (history or [])[-6:]
        )

        full_prompt = f"""
Eres un asistente pedagógico experto para docentes.

OBJETIVO:
- Responde de forma clara, didáctica y profesional.
- Usa primero el CONTEXTO (prontuario / embeddings).
- Si el contexto es insuficiente, USA INTERNET (Google Search tool) para complementar.
- No inventes: si no encuentras evidencia suficiente, dilo.

CONTEXTO (RAG):
{contexto}

HISTORIAL:
{historial}

PREGUNTA:
{prompt}

RESPUESTA:
"""

        # Config con herramienta google_search (grounding)
        config = types.GenerateContentConfig(
            tools=[self.grounding_tool],
        )

        # OJO: en docs el ejemplo usa gemini-3-flash-preview para grounding.
        # Puedes dejar gemini-2.5-flash si te funciona, pero para búsqueda web
        # recomiendo el modelo de la familia que soporta grounding consistentemente.
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="gemini-2.5-flash",
            contents=full_prompt,
            config=config,
        )

        return (response.text or "").strip()
