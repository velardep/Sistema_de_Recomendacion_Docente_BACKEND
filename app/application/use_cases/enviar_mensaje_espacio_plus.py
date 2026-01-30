from __future__ import annotations

from app.domain.ports.outbound.llm_client import LLMClient


class EnviarMensajeEspacioPlusUseCase:
    def __init__(
        self,
        auth_client,
        espacios_repo,
        chat_espacios_repo,
        recomendaciones_espacio_repo,
        orquestador_rag_espacio,
        llm_client: LLMClient,
    ):
        self.auth_client = auth_client
        self.espacios_repo = espacios_repo
        self.chat_espacios_repo = chat_espacios_repo
        self.recomendaciones_espacio_repo = recomendaciones_espacio_repo
        self.orquestador = orquestador_rag_espacio
        self.llm = llm_client

    async def execute(
        self,
        access_token: str,
        espacio_id: str,
        conversacion_espacio_id: str,
        content: str
    ):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        # 0) valida espacio (RLS)
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return None

        # 0.1) valida conversación (RLS)
        conv = await self.chat_espacios_repo.obtener_conversacion(access_token, conversacion_espacio_id)
        if not conv:
            return None

        # 1) guarda mensaje user
        user_msg = await self.chat_espacios_repo.insertar_mensaje(
            access_token=access_token,
            conversacion_espacio_id=conversacion_espacio_id,
            docente_id=docente_id,
            rol="user",
            contenido=content,
            metadatos={"espacio_id": espacio_id},
        )

        # 2) historial (últimos 6)
        history_rows = await self.chat_espacios_repo.listar_mensajes(access_token, conversacion_espacio_id)

        # tus filas vienen como: { rol: "user|assistant", contenido: "..." }
        history_fmt = [
            {"role": m.get("rol"), "content": m.get("contenido")}
            for m in (history_rows or [])
        ][-6:]


        # 3) RAG SOLO espacio
        resultados, chunks = await self.orquestador.buscar_contexto(
            access_token=access_token,
            docente_id=docente_id,
            espacio_id=espacio_id,
            consulta=content,
            top_k_espacio=6,
            incluir_prontuario=False,          # solo material del espacio
            top_k_prontuario=0,                # redundante pero explícito
            tipo_fuente_espacio="archivo",     # porque tu DB permite: prontuario/archivo/pdc/otro
        )


        # 4) Gemini redacta con contexto
        respuesta = await self.llm.generate(
            prompt=content,
            context_chunks=chunks,
            history=history_fmt,
        )

        # 5) guarda assistant
        assistant_msg = await self.chat_espacios_repo.insertar_mensaje(
            access_token=access_token,
            conversacion_espacio_id=conversacion_espacio_id,
            docente_id=docente_id,
            rol="assistant",
            contenido=respuesta,
            metadatos={
                "mode": "rag_espacio_gemini",
                "espacio_id": espacio_id,
                "chunks": len(chunks),
            },
        )

        # 6) renombrar conversación si está sin título o título genérico
        titulo_actual = (conv.get("titulo") or "").strip()
        if (not titulo_actual) or titulo_actual.lower() in {"chat", "nuevo chat", "chat espacio", "chat de espacio"}:
            nuevo_titulo = (content.strip().replace("\n", " "))[:60]
            try:
                conv = await self.chat_espacios_repo.actualizar_titulo_conversacion(
                    access_token,
                    conversacion_espacio_id,
                    nuevo_titulo
                )
            except Exception:
                # No rompemos el chat si el PATCH falla
                pass

        # 7) guardar recomendaciones internas (opcional pero útil para auditoría)
        recs = []
        for r in (resultados or [])[:6]:
            try:
                rec = await self.recomendaciones_espacio_repo.crear_recomendacion_espacio(
                    access_token,
                    {
                        "docente_id": docente_id,
                        "espacio_id": espacio_id,
                        "conversacion_espacio_id": conversacion_espacio_id,
                        "mensaje_id": assistant_msg.get("id"),
                        "tipo": "recurso",
                        "modelo": "embeddings",
                        "contenido": r.get("texto"),
                        "metadatos": {
                            "similitud": r.get("similitud"),
                            "score_ponderado": r.get("score_ponderado"),
                            "fuente_id": r.get("fuente_id"),
                            "tipo_fuente": r.get("tipo_fuente"),
                            "embedding_row_id": r.get("id"),
                        },
                    }
                )
                recs.append(rec)
            except Exception:
                pass

        # 8) devuelve también la conversación actualizada (para UI instantánea)
        try:
            conv_updated = await self.chat_espacios_repo.obtener_conversacion(access_token, conversacion_espacio_id)
        except Exception:
            conv_updated = conv

        return {
            "conversation": conv_updated,
            "user_message": user_msg,
            "assistant_message": assistant_msg,
            "recomendaciones": recs,
            # Si quieres debug interno: "chunks": chunks
        }
