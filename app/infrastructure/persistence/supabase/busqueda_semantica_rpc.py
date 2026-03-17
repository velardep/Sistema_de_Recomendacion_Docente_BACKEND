# app/infrastructure/persistence/supabase/busqueda_semantica_rpc.py

# Componente de persistencia encargado de ejecutar la función RPC
# `buscar_semantico` en Supabase. Recibe un embedding de consulta y filtros
# opcionales para recuperar fragmentos de texto similares desde la base de datos.

from __future__ import annotations
from typing import List

import httpx
import logging

log = logging.getLogger("rag.busqueda_rpc")

# Este adapter encapsula la llamada HTTP hacia la RPC de Supabase usada
# por los flujos de búsqueda semántica y RAG del sistema.
class BusquedaSemanticaRPC:
    def __init__(self, supabase_url: str, supabase_anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = supabase_anon_key

    async def buscar(
        self,
        *,
        access_token: str,
        query_vec: list[float],
        top_k: int = 5,
        tipo_fuente: str | None = None,
        espacio_id: str | None = None,
        docente_id: str | None = None,
    ) -> List[dict]:
        # Endpoint RPC de Supabase que ejecuta la búsqueda vectorial definida en la base de datos.
        url = f"{self.base}/rest/v1/rpc/buscar_semantico"

        # Cabeceras necesarias para autenticar la llamada contra Supabase usando
        # la anon key de la app y el token del usuario autenticado.
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Parámetros enviados a la RPC: Embedding de consulta, cantidad de resultados
        # y filtros opcionales para limitar la búsqueda por fuente, espacio o docente.
        payload = {
            "query_embedding": query_vec,
            "match_count": int(top_k),
            "filtro_tipo_fuente": tipo_fuente,
            "filtro_espacio_id": espacio_id,
            "filtro_docente_id": docente_id,
        }

        # LOogas para debug que muestran la URL, payload y resultados de la llamada RPC.
        log.debug("RPC buscar_semantico -> url=%s", url)
        log.debug("RPC payload -> top_k=%s tipo_fuente=%s espacio_id=%s docente_id=%s vec_len=%s",
                  top_k, tipo_fuente, espacio_id, docente_id, len(query_vec))

        # Ejecuta la llamada HTTP a la RPC de búsqueda semántica.
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=payload)

        log.debug("RPC status=%s body=%s", r.status_code, r.text[:5000])

        # Si Supabase devuelve error, se propaga como RuntimeError para que la capa superior decida cómo manejarlo.
        if r.status_code >= 400:
            raise RuntimeError(f"RPC buscar_semantico {r.status_code}: {r.text}")

        # La RPC debería devolver una lista de resultados, si no lo hace, se devuelve
        # lista vacía para mantener un contrato estable hacia capas superiores.
        data = r.json()
        if not isinstance(data, list):
            log.debug("RPC json no es lista: %s", type(data))
            return []

        log.debug("RPC rows=%s", len(data))
        if len(data) > 0:
            sample = data[0]
            log.debug("RPC sample keys=%s", list(sample.keys()))
            log.debug("RPC sample tipo_fuente=%s espacio_id(meta)=%s docente?=%s",
                      sample.get("tipo_fuente"),
                      (sample.get("metadatos") or {}).get("espacio_id"),
                      "docente_id" in sample)

        return data