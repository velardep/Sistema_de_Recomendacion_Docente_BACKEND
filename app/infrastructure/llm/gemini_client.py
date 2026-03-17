# app/infrastructure/llm/gemini_client.py

# Cliente de infraestructura encargado de comunicarse con Gemini para generar
# respuestas del sistema. Construye el prompt final con contexto RAG e historial,
# habilita grounding con Google Search y además registra datos de auditoría
# sobre entradas, latencia, tokens y uso efectivo del modelo.

from google import genai
from google.genai import types
from app.domain.ports.outbound.llm_client import LLMClient
from app.infrastructure.config.settings import settings
from typing import Optional

# Utilidades estándar usadas para auditoría, medición de latencia y manejo
# seguro de datos antes y después de llamar al modelo.
import asyncio
import logging
import time
import json

# Logger dedicado al cliente Gemini para registrar auditoría técnica del uso del LLM.
logger = logging.getLogger("llm.gemini")

# Convierte valores a entero de forma segura para evitar errores en logs
# cuando algún campo venga nulo o con tipo inesperado.
def _safe_int(x):
    try:
        return int(x) if x is not None else None
    except Exception:
        return None

# Calcula la longitud de un valor de forma segura, devolviendo 0 si no se
# puede medir correctamente.
def _safe_len(s):
    try:
        return len(s) if s is not None else 0
    except Exception:
        return 0

# Suma la cantidad total de caracteres de una lista de textos, útil para
# auditoría del tamaño real enviado al modelo.
def _sum_chars(items: list[str]) -> int:
    total = 0
    for it in items or []:
        total += _safe_len(it)
    return total

# Implementación concreta del puerto LLMClient usando Gemini como proveedor.
# Este componente centraliza la llamada al modelo y el uso opcional de grounding.
class GeminiClient(LLMClient):
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Configura la herramienta oficial de Google Search para grounding, de modo
        # que Gemini pueda apoyarse en búsqueda web cuando el contexto local no baste.
        self.grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

    # Método principal para generar una respuesta con Gemini. Recibe la pregunta,
    # contexto RAG, historial y metadatos opcionales de auditoría, y devuelve
    # únicamente el texto generado por el modelo.
    async def generate(
        self,
        *,
        prompt: str,
        context_chunks: list[str],
        history: list[dict],
        module: str = "unknown",              # ej: "chat_general" | "chat_contextual" | "redaccion_doc"
        request_id: Optional[str] = None,     # id para rastrear en logs (uuid/string)
        user_id: Optional[str] = None,        
        chat_id: Optional[str] = None,       

        # Control de cuántos mensajes del historial se manda como contexto (mantiene 6 por defecto)
        history_tail: int = 6,
    ) -> str:
    
        # Limita el tamaño de cada chunk recuperado por RAG antes de armar el prompt,
        # para reducir consumo de tokens sin perder por completo el contexto relevante.
        MAX_CHUNK_CHARS = 1000

        trimmed_chunks = []
        for c in (context_chunks or []):
            if not c:
                continue
            txt = c.strip()
            if len(txt) > MAX_CHUNK_CHARS:
                txt = txt[:MAX_CHUNK_CHARS] + "..."
            trimmed_chunks.append(txt)

        contexto = "\n".join(f"- {c}" for c in trimmed_chunks)

        # Toma solo la cola reciente del historial conversacional para controlar tamaño
        # del prompt y mantener continuidad sin enviar toda la conversación completa.
        tail = (history or [])[-history_tail:] if history_tail and history else (history or [])
        historial = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in tail
            if isinstance(m, dict) and "role" in m and "content" in m
        )

        # Construye el prompt final que combina instrucciones del sistema, contexto RAG,
        # historial reciente y pregunta actual del usuario.
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
""".strip()

        # Configuración del modelo con la herramienta de grounding habilitada.
        # La decisión de usarla o no queda en manos del propio modelo.
        config = types.GenerateContentConfig(
            tools=[self.grounding_tool],
        )

        # Registra una auditoría previa a la llamada con métricas reales del prompt:
        # historial enviado, chunks RAG usados, tamaño de entrada y configuración aplicada.
        pre = {
            "event": "llm_request",
            "provider": "google_gemini",
            "model": "gemini-2.5-flash",
            "module": module,
            "request_id": request_id,
            "user_id": user_id,
            "chat_id": chat_id,

            # Datos reales de entrada
            "history_msgs_sent": _safe_int(len(tail)),
            "history_chars_sent": _safe_int(_sum_chars([m.get("content", "") for m in tail if isinstance(m, dict)])),
            "rag_chunks_sent": _safe_int(len(trimmed_chunks)),
            "rag_chars_sent": _safe_int(_sum_chars(trimmed_chunks)),
            "question_chars": _safe_int(_safe_len(prompt)),
            "full_prompt_chars": _safe_int(_safe_len(full_prompt)),

            # Config relevante 
            "grounding_configured": True,
        }
        logger.debug(json.dumps(pre, ensure_ascii=False))

        # Ejecuta la llamada real a Gemini y mide la latencia total de respuesta.
        t0 = time.perf_counter()
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="gemini-2.5-flash",
            contents=full_prompt,
            config=config,
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0

        # Extrae, si están disponibles, las métricas reales de consumo de tokens
        # reportadas por Gemini para esta generación.
        um = getattr(response, "usage_metadata", None)
        prompt_tokens = _safe_int(getattr(um, "prompt_token_count", None)) if um else None
        resp_tokens = _safe_int(getattr(um, "candidates_token_count", None)) if um else None
        total_tokens = _safe_int(getattr(um, "total_token_count", None)) if um else None

        # Intenta detectar si la respuesta del modelo incluyó señales de grounding,
        # sin asumir una estructura fija para no romper compatibilidad entre versiones.
        grounding_present = False
        grounding_details = None

        try:
            # Algunas respuestas incluyen candidates, grounding_metadata, etc.
            candidates = getattr(response, "candidates", None)
            if candidates and len(candidates) > 0:
                c0 = candidates[0]
                # Campo a veces: grounding_metadata / groundingMetadata (según versión)
                gm = getattr(c0, "grounding_metadata", None) or getattr(c0, "groundingMetadata", None)
                if gm:
                    grounding_present = True
                    # No volcamos todo para no llenar consola; dejamos un resumen de “existe”
                    grounding_details = {"present": True}
        except Exception:
            # Si cambia la estructura, no se rompe nada
            grounding_present = False
            grounding_details = None

        # Extrae el texto final generado por Gemini como salida utilizable por el sistema.
        text_out = (getattr(response, "text", None) or "").strip()

        # Registra auditoría posterior a la llamada con latencia, consumo de tokens,
        # tamaño de salida y presencia de grounding en la respuesta.
        post = {
            "event": "llm_response",
            "provider": "google_gemini",
            "model": "gemini-2.5-flash",
            "module": module,
            "request_id": request_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "latency_ms": round(dt_ms, 2),

            # Tokens reales
            "prompt_tokens": prompt_tokens,
            "response_tokens": resp_tokens,
            "total_tokens": total_tokens,

            # Salida
            "output_chars": _safe_int(_safe_len(text_out)),

            # Grounding (solo presencia)
            "grounding_present": grounding_present,
            "grounding_details": grounding_details,
        }
        logger.debug(json.dumps(post, ensure_ascii=False))

        return text_out