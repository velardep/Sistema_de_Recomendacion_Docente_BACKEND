from __future__ import annotations

from typing import Any, Tuple, List


# app/application/services/orquestador_recomendaciones.py
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
        recomendaciones = await self.recomendar_desde_prontuario(
            access_token=access_token,
            docente_id=docente_id,
            conversacion_id=conversacion_id,
            mensaje_id=mensaje_id,
            consulta=consulta,
            top_k=top_k,
        )

        # chunks = textos que el LLM verá como contexto
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
        vec = self.embeddings_model.embed(consulta)

        resultados = await self.busqueda_rpc.buscar(
            access_token=access_token,
            query_vec=vec,
            top_k=top_k,
            tipo_fuente="prontuario",
            espacio_id=None,
            docente_id=docente_id,
        )

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
