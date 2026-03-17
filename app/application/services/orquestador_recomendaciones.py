# app/application/services/orquestador_recomendaciones.py

# Servicio de aplicación del flujo de CHAT GENERAL encargado de recuperar
# contenido relevante desde el prontuario mediante embeddings, convertirlo
# en recomendaciones persistidas en base de datos y devolver también los
# chunks que el LLM usará como contexto.

from __future__ import annotations
from typing import Any, Tuple, List

# Este servicio orquesta la recuperación de recursos desde prontuario y su
# conversión a recomendaciones almacenadas, dejando el use case del chat
# más limpio y enfocado en el flujo conversacional.
class OrquestadorRecomendaciones:
    def __init__(self, embeddings_model, busqueda_rpc, recomendacion_repo):
        self.embeddings_model = embeddings_model
        self.busqueda_rpc = busqueda_rpc
        self.recomendacion_repo = recomendacion_repo

    async def ejecutar(
        self,
        *,
        access_token: str,
        docente_id: str,
        conversacion_id: str,
        mensaje_id: str,
        consulta: str,
        top_k: int = 3,
    ):
        # Ejecuta la recomendación desde prontuario y reutiliza el contenido de esas
        # recomendaciones como contexto textual para el LLM.
        recomendaciones = await self.recomendar_desde_prontuario(
            access_token=access_token,
            docente_id=docente_id,
            conversacion_id=conversacion_id,
            mensaje_id=mensaje_id,
            consulta=consulta,
            top_k=top_k,
        )

        chunks = [r.get("contenido", "") for r in recomendaciones]
        return recomendaciones, chunks

    async def recomendar_desde_prontuario(
        self,
        access_token: str,
        docente_id: str,
        conversacion_id: str,
        mensaje_id: str,
        consulta: str,
        top_k: int = 3,
    ):
        # Genera el embedding de la consulta para buscar recursos semánticamente
        # relacionados dentro del prontuario.
        vec = self.embeddings_model.embed(consulta)

        # Consulta el prontuario global mediante búsqueda semántica para recuperar
        # los fragmentos más cercanos a la consulta del docente.
        resultados = await self.busqueda_rpc.buscar(
            access_token=access_token,
            query_vec=vec,
            top_k=top_k,
            tipo_fuente="prontuario",
            espacio_id=None,
            docente_id=docente_id,
        )

        # Cada resultado recuperado se transforma en una recomendación persistida,
        # de modo que quede trazabilidad entre el mensaje, el recurso sugerido y
        # la conversación donde fue utilizado.
        recomendaciones = []
        for r in resultados:
            rec_payload = {
                "docente_id": docente_id,
                "conversacion_id": conversacion_id,
                "mensaje_id": mensaje_id,
                "tipo": "recurso",
                "modelo": "embeddings",
                "contenido": r["texto"],
                "metadatos": {
                    "similitud": r.get("similitud"),
                    "fuente_id": r.get("fuente_id"),
                    "tipo_fuente": r.get("tipo_fuente"),
                    "embedding_row_id": r.get("id"),
                },
            }
            created = await self.recomendacion_repo.crear_recomendacion(access_token, rec_payload)
            recomendaciones.append(created)

        return recomendaciones
