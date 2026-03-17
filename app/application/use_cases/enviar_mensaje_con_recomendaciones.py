# app/application/use_cases/enviar_mensaje_con_recomendaciones.py

# Use case principal del flujo de CHAT GENERAL. Se encarga de procesar un mensaje
# del docente dentro de una conversación general: validar al usuario, actualizar
# el título del chat si sigue siendo genérico, guardar el mensaje del usuario,
# recuperar historial y contexto mediante RAG, generar la respuesta con el LLM,
# guardar la respuesta del asistente y registrar actividad en RED3.

import re
import unicodedata

from app.domain.ports.outbound.llm_client import LLMClient
from app.infrastructure.persistence.supabase.chat_repository_postgrest import is_generic_title

# Palabras muy comunes o genéricas que se excluyen al intentar construir
# automáticamente un título útil a partir del primer mensaje del usuario.
STOPWORDS = {
    # súper comunes
    "que","como","cual","cuáles","cual es","cuales","donde","cuando","por","para","con","sin","sobre","entre",
    "un","una","unos","unas","el","la","los","las","de","del","al","y","o","u","en","a","mi","mis","tu","tus",
    "me","te","se","lo","le","les","ya","si","no","sí","más","muy","tambien","también",
    # verbos/genéricos típicos de chat
    "puedes","podrias","podrías","ayudar","ayuda","dime","dame","haz","hace","hacer","explica","explicame","explicación",
    "ejemplo","ejemplos","ejercicio","ejercicios","problema","problemas","tarea","tareas",
    "quiero","necesito","recomienda","recomendacion","recomendación",
    # relleno
    "porfavor","por favor","ok","hola","buenas","buenos","gracias",
}

# Pistas de temas frecuentes detectadas para generar títulos
# más claros y consistentes en conversaciones nuevas.
TOPIC_HINTS = [
    # (regex -> titulo base)
    (r"\bdivision(es)?\b", "División"),
    (r"\bmultiplicacion(es)?\b", "Multiplicación"),
    (r"\bfraccion(es)?\b", "Fracciones"),
    (r"\bporcentaje(s)?\b", "Porcentajes"),
    (r"\becuacion(es)?\b", "Ecuaciones"),
    (r"\b(derivad|integral|limite)s?\b", "Cálculo"),
    (r"\bfotosintesis\b", "Fotosíntesis"),
    (r"\bcelula(s)?\b", "Células"),
    (r"\bquimica\b", "Química"),
    (r"\b(gramatica|ortografia|lectura|redaccion)\b", "Lengua"),
]

# Sufijos opcionales que completan el título según la intención detectada
# en el mensaje, por ejemplo ejercicios, ejemplos o explicación.
ACTION_SUFFIX = [
    (r"\bejercicios?\b|\bpractica\b|\bpráctica\b", " – ejercicios"),
    (r"\bejemplo(s)?\b", " – ejemplos"),
    (r"\bexplica\b|\bexplicame\b|\bexplicación\b|\bteoria\b|\bteoría\b", " – explicación"),
    (r"\bguia\b|\bguía\b|\bplan\b|\bclase\b", " – guía"),
]

# Normaliza el texto para facilitar la detección de temas e intenciones al
# construir títulos: pasa a minúsculas, quita tildes y limpia caracteres.
def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # quita tildes
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# Genera un título corto y más legible para el chat a partir del primer mensaje
# del usuario, evitando títulos vacíos o demasiado genéricos.
def build_pretty_title_from_message(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return "Conversación"
    t = _norm(raw)

    # 1) casos ultra genéricos: “en qué me puedes ayudar”, “hola”, etc.
    if re.search(r"\b(en que|en qué)\b.*\bayud", t) or t in {"ayuda", "ayudame", "hola", "buenas"}:
        return "Ayuda general"

    # 2) Detectar tema fuerte por hints (si existe)
    topic = None
    for pat, label in TOPIC_HINTS:
        if re.search(pat, t):
            topic = label
            break

    # 3) Detectar sufijo por intención (ejercicios/guía/explicación)
    suffix = ""
    for pat, sfx in ACTION_SUFFIX:
        if re.search(pat, t):
            suffix = sfx
            break

    # 4) Detectar “para niños”, “para 3ro”, etc.
    audience = ""
    if re.search(r"\bni(n|ñ)os?\b|\binfantil\b|\bprimaria\b", t):
        audience = " para niños"
    # (si se requiere, aquí se puede añadir “3ro primaria”, “secundaria”, etc.)

    # 5) Si no hubo tema por hints, construir uno por “palabras útiles”
    if not topic:
        words = [w for w in t.split() if w not in STOPWORDS and len(w) >= 4]
        # prioridad: primeras 2–3 palabras útiles
        core = " ".join(words[:3]).strip()
        if not core:
            return "Conversación"
        # capitaliza simple
        topic = core[:1].upper() + core[1:]

    # 6) Armar título final
    title = f"{topic}{audience}{suffix}".strip()

    # 7) Limitar longitud
    if len(title) > 52:
        title = title[:49].rstrip() + "..."

    return title


class EnviarMensajeConRecomendacionesUseCase:
    def __init__(
        self,
        auth_client,
        chat_repo,
        orquestador,
        llm_client: LLMClient,
        red3_service=None,
    ):
        self.auth = auth_client
        self.chat_repo = chat_repo
        self.orquestador = orquestador
        self.llm = llm_client
        self.red3 = red3_service

    async def execute(self, token: str, chat_id: str, content: str):

        # Primero se identifica al docente autenticado y, si el chat todavía tiene un
        # título genérico, se intenta reemplazar por uno generado desde el mensaje actual.
        user = await self.auth.get_user(token)
        docente_id = user["id"]

        # Si el chat no tiene título “útil”, lo ponemos con la primera consulta
        conv = await self.chat_repo.get_conversation(token, chat_id)
        if conv and is_generic_title(conv.get("titulo")):
            try:
                new_title = build_pretty_title_from_message(content)
                await self.chat_repo.update_conversation_title(token, chat_id, new_title)
            except Exception:
                pass 

        # Se guarda el mensaje del usuario antes de ejecutar RAG o generar respuesta
        # para que la conversación quede persistida desde el inicio del flujo.
        user_msg = await self.chat_repo.insert_message(
            token,
            conversation_id=chat_id,
            docente_id=docente_id,
            role="user",
            content=content,
            meta={},
        )
        user_msg_id = user_msg["id"]


        # Si RED3 está disponible, se registra este mensaje como evento de actividad
        # del docente dentro del chat general sin interrumpir el flujo principal.

        # RED3 EVENT: USER CHAT_MESSAGE
        if self.red3:
            try:
                await self.red3.record_event_best_effort(
                    token,
                    docente_id=docente_id,
                    event_type="chat_message",
                    conversation_id=chat_id,
                    espacio_id=None,
                    # META (json)
                    meta={
                        "scope": "general",
                        "role": "user",
                        "message_id": user_msg_id,
                        "text": content,
                    },
                )
            except Exception:
                pass

        # Recupera el historial del chat y lo adapta al formato esperado por el LLM
        # para mantener continuidad conversacional en la respuesta.
        history = await self.chat_repo.get_history(token, chat_id)
        history_fmt = [{"role": m["role"], "content": m["content"]} for m in history]

        # Ejecuta el flujo RAG del chat general para recuperar contexto relevante
        # desde embeddings antes de generar la respuesta del asistente. (embeddings/pgvector)
        chunks = await self.orquestador.ejecutar(
            access_token=token,
            docente_id=docente_id,
            conversacion_id=chat_id,
            mensaje_id=user_msg_id,
            consulta=content,
        )

        # Genera la respuesta final usando la consulta original, el historial del chat
        # y los chunks recuperados por el orquestador.
        # Gemini (LLM): usa primero chunks y si no alcanza usa INTERNET (grounding)
        respuesta = await self.llm.generate(
            prompt=content,
            context_chunks=chunks,
            history=history_fmt,
        )

        # Persiste la respuesta del assistant junto con metadatos mínimos del uso de RAG.
        assistant_msg = await self.chat_repo.insert_message(
            token,
            conversation_id=chat_id,
            docente_id=docente_id,
            role="assistant",
            content=respuesta,
            meta={
                "rag_chunks_count": len(chunks),
                # Si luego se requiere guardar citas, aquí va (por ahora texto simple)
            },
        )

        # También se registra la respuesta del assistant como evento para dejar trazado
        # completo del intercambio dentro del flujo de monitoreo de RED3.

        # RED3 EVENT: ASSISTANT CHAT_MESSAGE

        # IGUAL: event_type='chat_message', role='assistant'
        if self.red3:
            try:
                await self.red3.record_event_best_effort(
                    token,
                    docente_id=docente_id,
                    event_type="chat_message",
                    # TOP-LEVEL (tabla)
                    conversation_id=chat_id,
                    espacio_id=None,
                    # META
                    meta={
                        "scope": "general",
                        "role": "assistant",
                        "message_id": assistant_msg["id"],
                        "text": respuesta,
                        "chunks_used": len(chunks),
                    },
                )
            except Exception:
                pass

        # Al final se intenta recalcular el perfil resumido del docente con base en la
        # actividad reciente del chat, sin romper la conversación si esta etapa falla.

        # RED3 SNAPSHOT + PROFILE UPDATE 

        # Esto llena: red3_docente_feature_snapshots + red3_docente_style_profiles
        if self.red3:
            try:
                await self.red3.update_profile_best_effort(
                    token,
                    docente_id=docente_id,
                    window_days=30,
                )
            except Exception:
                pass

        # Devuelve ambos mensajes y la conversación actualizada para refrescar la UI
        # inmediatamente después de la interacción.
        updated_conv = await self.chat_repo.get_conversation(token, chat_id)
        
        return {
            "user_message": user_msg,
            "assistant_message": assistant_msg,
            "conversation": updated_conv,
        }
