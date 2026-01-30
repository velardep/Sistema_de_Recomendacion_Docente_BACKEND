from __future__ import annotations
from typing import Any, List, Tuple


class OrquestadorRAGEspacio:
    """
    Orquestador RAG para chat contextual de ESPACIOS.

    - Prioriza embeddings del espacio (tipo_fuente="espacio_doc" por defecto)
    - Opcionalmente puede complementar con prontuario (tipo_fuente="prontuario")
    - Devuelve chunks (strings) para pasar al LLM
    """

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
        tipo_fuente_espacio: str = "espacio_doc",
    ) -> Tuple[List[dict], List[str]]:
        """
        Retorna:
          - resultados_raw: lista de filas devueltas por RPC (mezcla espacio + prontuario si aplica)
          - chunks: lista[str] lista para el prompt del LLM
        """

        # 1) embedding consulta
        vec = self.embeddings_model.embed(consulta)

        resultados: List[dict] = []

        # 2) buscar en espacio (RAG propio)
        res_espacio = await self.busqueda_rpc.buscar(
            access_token=access_token,
            query_vec=vec,
            top_k=top_k_espacio,
            tipo_fuente=tipo_fuente_espacio,
            espacio_id=espacio_id,
            docente_id=docente_id,
        )
        if res_espacio:
            resultados.extend(res_espacio)

        # 3) complementar con prontuario si hace falta (y si el flag está activo)
        if incluir_prontuario and top_k_prontuario > 0:
            res_pront = await self.busqueda_rpc.buscar(
                access_token=access_token,
                query_vec=vec,
                top_k=top_k_prontuario,
                tipo_fuente="prontuario",
                espacio_id=None,
                docente_id=docente_id,
            )
            if res_pront:
                resultados.extend(res_pront)

        # 4) mapear a chunks de texto para el LLM (limpio y corto)
        chunks: List[str] = []
        for r in resultados:
            texto = (r.get("texto") or "").strip()
            if not texto:
                continue

            origen = r.get("tipo_fuente") or r.get("origen") or "contexto"
            sim = r.get("similitud")
            pref = f"[{origen}]"
            if sim is not None:
                pref = f"[{origen} sim={sim:.3f}]"

            chunks.append(f"{pref} {texto}")

        return resultados, chunks
