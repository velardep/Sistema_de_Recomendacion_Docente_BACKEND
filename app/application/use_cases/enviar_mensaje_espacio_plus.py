# app/application/use_cases/enviar_mensaje_espacio_plus.py

# Este use case pertenece principalmente al flujo de ESPACIOS DE TRABAJO, pero
# también integra EMBEDDINGS, RED1, RED2 y RED3 dentro del chat contextual por
# espacio. 
# Su responsabilidad es procesar un mensaje del docente dentro de una
# conversación de espacio: validar acceso, guardar el mensaje, clasificarlo,
# recuperar contexto relevante solo de ese espacio mediante RAG, generar la
# respuesta con el LLM, guardar la respuesta del asistente y actualizar señales
# de seguimiento del usuario cuando corresponda.

from __future__ import annotations
from app.domain.ports.outbound.llm_client import LLMClient
from app.application.use_cases.enviar_mensaje_con_recomendaciones import build_pretty_title_from_message


class EnviarMensajeEspacioPlusUseCase:
    def __init__(
        self,
        auth_client,
        espacios_repo,
        chat_espacios_repo,
        orquestador_rag_espacio,
        llm_client: LLMClient,
        red1_service,
        red2_guidance_service=None,
        red3_service=None,
    ):
        self.auth_client = auth_client
        self.espacios_repo = espacios_repo
        self.chat_espacios_repo = chat_espacios_repo
        self.orquestador = orquestador_rag_espacio
        self.llm = llm_client
        self.red1 = red1_service
        self.red2_guidance = red2_guidance_service
        self.red3 = red3_service

    async def execute(
        self,
        access_token: str,
        espacio_id: str,
        conversacion_espacio_id: str,
        content: str
    ):
        
        # Primero se identifica al docente autenticado y se valida que tanto el espacio
        # como la conversación existan y sean accesibles bajo las reglas de seguridad.
        # Si alguna de esas validaciones falla, el flujo se corta inmediatamente.
        
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        # Valida espacio (RLS)
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return None

        # Valida conversación (RLS)
        conv = await self.chat_espacios_repo.obtener_conversacion(access_token, conversacion_espacio_id)
        if not conv:
            return None

        # Guarda mensaje user
        # El mensaje del usuario se persiste antes de cualquier procesamiento adicional
        # para que la conversación quede registrada incluso si alguna etapa posterior
        # falla de forma parcial.
        user_msg = await self.chat_espacios_repo.insertar_mensaje(
            access_token=access_token,
            conversacion_espacio_id=conversacion_espacio_id,
            docente_id=docente_id,
            rol="user",
            contenido=content,
            metadatos={"espacio_id": espacio_id},
        )

        # Si RED3 está disponible, se registra el mensaje del usuario como evento de
        # seguimiento. Esto alimenta el monitoreo del comportamiento docente sin romper
        # el flujo principal si ocurre algún error.

        # RED3 EVENT: USER CHAT_MESSAGE ESPACIO
        if self.red3:
            try:
                await self.red3.record_event_best_effort(
                    access_token,
                    docente_id=docente_id,
                    event_type="chat_message",
                    # TOP-LEVEL TABLA
                    espacio_id=espacio_id,
                    conversation_id=conversacion_espacio_id,
                    # META
                    meta={
                        "scope": "espacio",
                        "role": "user",
                        "message_id": user_msg.get("id"),
                        "text": content,
                        "conversacion_espacio_id": conversacion_espacio_id,
                    },
                )
            except Exception:
                pass

        # Luego se intenta clasificar el mensaje con RED1 para generar etiquetas útiles
        # para análisis y recomendación.

        # RED 1: clasificar mensaje del usuario y guardar (best-effort)
        try:
            await self.red1.clasificar_y_guardar(
                access_token,
                docente_id=docente_id,
                espacio_id=espacio_id,
                conversacion_espacio_id=conversacion_espacio_id,
                mensaje_espacio_id=user_msg.get("id"),
                tipo_fuente="mensaje",
                fuente_id=None,
                chunk_index=None,
                texto=content,
            )
        except Exception:
            pass

        # Se recupera una ventana corta del historial reciente y se adapta al formato
        # esperado por el LLM para mantener continuidad conversacional sin enviar toda
        # la conversación completa.

        # Historial (últimos 6 mensajes)
        history_rows = await self.chat_espacios_repo.listar_mensajes(access_token, conversacion_espacio_id)

        # Las flas vienen como: { rol: "user|assistant", contenido: "..." }
        history_fmt = [
            {"role": m.get("rol"), "content": m.get("contenido")}
            for m in (history_rows or [])
        ][-6:]


        # Se ejecuta la búsqueda de contexto usando únicamente material asociado al
        # espacio actual.

        # RAG SOLO espacio
        resultados, chunks = await self.orquestador.buscar_contexto(
            access_token=access_token,
            docente_id=docente_id,
            espacio_id=espacio_id,
            consulta=content,
            top_k_espacio=6,
            incluir_prontuario=False,          # solo material del espacio
            top_k_prontuario=0,                # redundante pero explícito
            tipo_fuente_espacio="archivo",     # DB permite: prontuario/archivo/pdc/otro
        )


        # Si RED2 está disponible, se construye una guía didáctica adicional a partir
        # de los resultados recuperados por RAG para orientar mejor la respuesta final.

        # Gemini redacta con contexto
        guide = None
        if self.red2_guidance:
            try:
                guide = await self.red2_guidance.build_guidance_from_rag_resultados(
                    access_token=access_token,
                    resultados=resultados,
                    top_k=5,
                )
            except Exception:
                guide = None

        # La consulta original puede enriquecerse con una instrucción didáctica previa
        # para forzar que la respuesta del modelo siga una orientación pedagógica más útil.
        prompt_final = content
        if guide:
            prompt_final = (
                "INSTRUCCIÓN DIDÁCTICA (obligatoria):\n"
                f"- {guide}\n\n"
                "Consulta del docente:\n"
                f"{content}"
            )

        # Con el prompt final, el historial reciente y los fragmentos recuperados del
        # espacio, se genera la respuesta contextual del asistente.
        respuesta = await self.llm.generate(
            prompt=prompt_final,
            context_chunks=chunks,
            history=history_fmt,
        )

        # La respuesta generada también se persiste como mensaje de assistant para que
        # la conversación quede completa y reutilizable en interacciones posteriores.
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

        # También se registra la respuesta del asistente como evento de RED3 para dejar
        # trazabilidad del intercambio completo dentro del espacio.

        # RED3 EVENT: ASSISTANT CHAT_MESSAGE ESPACIO
        if self.red3:
            try:
                await self.red3.record_event_best_effort(
                    access_token,
                    docente_id=docente_id,
                    event_type="chat_message",
                    espacio_id=espacio_id,
                    conversation_id=conversacion_espacio_id,
                    # META
                    meta={
                        "scope": "espacio",
                        "role": "assistant",
                        "message_id": assistant_msg.get("id"),
                        "text": respuesta,
                        "chunks_used": len(chunks),
                        "conversacion_espacio_id": conversacion_espacio_id,
                    },
                )
            except Exception:
                pass
      
        # Si la conversación todavía tiene un título vacío o demasiado genérico, se
        # intenta generar uno más representativo a partir del primer mensaje del usuario.
        titulo_actual = (conv.get("titulo") or "").strip()
        if (not titulo_actual) or titulo_actual.strip().lower() in {
            "chat", "nuevo chat", "chat espacio", "chat de espacio", "conversación", "conversacion"
        }:
            try:
                nuevo_titulo = build_pretty_title_from_message(content)
                conv = await self.chat_espacios_repo.actualizar_titulo_conversacion(
                    access_token,
                    conversacion_espacio_id,
                    nuevo_titulo
                )
            except Exception:
                pass
        

        # Al final se actualizar el perfil resumido del docente en RED3 usando
        # la actividad reciente.

        # RED3 SNAPSHOT + PROFILE UPDATE
        if self.red3:
            try:
                await self.red3.update_profile_best_effort(
                    access_token,
                    docente_id=docente_id,
                    window_days=30,
                )
            except Exception:
                pass
  
        # Se devuelve la conversación actualizada junto con ambos mensajes para que la
        # interfaz pueda refrescar el estado inmediatamente después de responder.
        recs = []
        try:
            conv_updated = await self.chat_espacios_repo.obtener_conversacion(access_token, conversacion_espacio_id)
        except Exception:
            conv_updated = conv

        return {
            "conversation": conv_updated,
            "user_message": user_msg,
            "assistant_message": assistant_msg,
            "recomendaciones": recs,
        }
