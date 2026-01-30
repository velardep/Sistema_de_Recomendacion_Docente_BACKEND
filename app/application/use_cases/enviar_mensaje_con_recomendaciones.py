# app/application/use_cases/enviar_mensaje_con_recomendaciones.py
from app.domain.ports.outbound.llm_client import LLMClient
from app.infrastructure.persistence.supabase.chat_repository_postgrest import is_generic_title


def build_title_from_first_question(text: str) -> str:
    t = " ".join((text or "").strip().split())
    if not t:
        return "Conversación"
    # título corto tipo “Pregunta: ...”
    if len(t) > 60:
        t = t[:57].rstrip() + "..."
    return t


class EnviarMensajeConRecomendacionesUseCase:
    def __init__(
        self,
        auth_client,
        chat_repo,
        recomendacion_repo,
        orquestador,
        llm_client: LLMClient,
    ):
        self.auth = auth_client
        self.chat_repo = chat_repo
        self.recomendacion_repo = recomendacion_repo
        self.orquestador = orquestador
        self.llm = llm_client

    async def execute(self, token: str, chat_id: str, content: str):
        user = await self.auth.get_user(token)
        docente_id = user["id"]

        # (0) si el chat no tiene título “útil”, lo ponemos con la primera consulta
        conv = await self.chat_repo.get_conversation(token, chat_id)
        if conv and is_generic_title(conv.get("titulo")):
            new_title = build_title_from_first_question(content)
            await self.chat_repo.update_conversation_title(token, chat_id, new_title)

        # (1) guardar mensaje usuario
        user_msg = await self.chat_repo.insert_message(
            token,
            conversation_id=chat_id,
            docente_id=docente_id,
            role="user",
            content=content,
            meta={},
        )
        user_msg_id = user_msg["id"]

        # (2) historial para LLM
        history = await self.chat_repo.get_history(token, chat_id)
        history_fmt = [{"role": m["role"], "content": m["content"]} for m in history]

        # (3) RAG: prontuario (embeddings/pgvector)
        recomendaciones, chunks = await self.orquestador.ejecutar(
            access_token=token,
            docente_id=docente_id,
            conversacion_id=chat_id,
            mensaje_id=user_msg_id,
            consulta=content,
        )

        # (4) Gemini: usa primero chunks, y si no alcanza usa INTERNET (grounding)
        respuesta = await self.llm.generate(
            prompt=content,
            context_chunks=chunks,
            history=history_fmt,
        )

        # (5) guardar mensaje assistant
        assistant_msg = await self.chat_repo.insert_message(
            token,
            conversation_id=chat_id,
            docente_id=docente_id,
            role="assistant",
            content=respuesta,
            meta={
                "rag_chunks_count": len(chunks),
                # Si luego quieres guardar citas, aquí va (por ahora texto simple)
            },
        )

        # (6) recomendaciones quedan internas (ya las guardaste al crear recomendación)
        # Si tu repo ya las inserta dentro del orquestador, NO dupliques aquí.

        updated_conv = await self.chat_repo.get_conversation(token, chat_id)
        
        return {
            "user_message": user_msg,
            "assistant_message": assistant_msg,
            "conversation": updated_conv,

        }
