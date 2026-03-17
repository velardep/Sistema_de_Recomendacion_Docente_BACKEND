# app/application/services/orquestador_rag_espacio.py

# Servicio de aplicación del flujo de ESPACIOS DE TRABAJO encargado de recuperar
# contexto semántico para el chat de un espacio. Puede buscar tanto en material
# propio del espacio como en prontuario global, y devuelve los resultados crudos
# junto con los chunks de texto que luego usará el LLM como contexto.

from __future__ import annotations

import logging

from typing import Any, List, Tuple

log = logging.getLogger("rag.espacio")

# Este servicio centraliza la lógica de recuperación de contexto para el chat
# por espacio, evitando que el use case tenga que resolver directamente la
# búsqueda semántica en múltiples fuentes.
class OrquestadorRAGEspacio:
    def __init__(self, embeddings_model, busqueda_rpc):
        self.embeddings_model = embeddings_model
        self.busqueda_rpc = busqueda_rpc

    async def buscar_contexto(
        self,
        *,
        access_token: str,
        docente_id: str,
        espacio_id: str,
        consulta: str,
        top_k_espacio: int = 6,
        top_k_prontuario: int = 2,
        incluir_prontuario: bool = True,
        tipo_fuente_espacio: str = "archivo",
    ) -> Tuple[List[dict], List[str]]:

        # Convierte la consulta del docente en un embedding para poder buscar fragmentos
        # semánticamente similares en la base de datos.
        vec = self.embeddings_model.embed(consulta)
        log.debug("RAG espacio -> consulta_len=%s vec_len=%s espacio_id=%s docente_id=%s",
                  len(consulta or ""), len(vec), espacio_id, docente_id)

        resultados: List[dict] = []

        # Primera fuente: Material asociado al espacio actual. Este suele ser el
        # contexto principal del chat cuando se trabaja dentro de un espacio específico.
        res_espacio = await self.busqueda_rpc.buscar(
            access_token=access_token,
            query_vec=vec,
            top_k=top_k_espacio,
            tipo_fuente=tipo_fuente_espacio,
            espacio_id=espacio_id,
            docente_id=docente_id,
        )

        log.debug("RAG espacio -> res_espacio=%s (tipo_fuente=%s)", len(res_espacio or []), tipo_fuente_espacio)

        if res_espacio:
            resultados.extend(res_espacio)

        # Segunda fuente opcional: Prontuario global. Solo se consulta si el flujo
        # que llama a este servicio decide habilitarlo explícitamente.
        if incluir_prontuario and top_k_prontuario > 0:
            res_pront = await self.busqueda_rpc.buscar(
                access_token=access_token,
                query_vec=vec,
                top_k=top_k_prontuario,
                tipo_fuente="prontuario",
                espacio_id=None,
                docente_id=docente_id,
            )
            log.debug("RAG espacio -> res_pront=%s", len(res_pront or []))
            if res_pront:
                resultados.extend(res_pront)

        # A partir de los resultados recuperados se arma la lista de chunks de texto
        # que será enviada al LLM como contexto de apoyo para responder.
        chunks: List[str] = []
        for r in resultados:
            texto = (r.get("texto") or "").strip()
            if not texto:
                continue
            chunks.append(texto)

        log.debug("RAG espacio -> resultados_total=%s chunks=%s", len(resultados), len(chunks))
        return resultados, chunks