# app/infrastructure/persistence/supabase/red2_repo.py

# Repositorio de persistencia encargado de guardar resultados de RED2 y
# recuperar etiquetas asociadas a embeddings ya procesados. Soporta inserción
# por lotes, upsert de resúmenes y lectura por ids de embeddings.

import httpx
from typing import Any, Dict, List, Optional

# Este adapter centraliza la lectura y escritura de datos auxiliares de RED2
# en tablas y vistas de Supabase.
class Red2Repo:
    def __init__(self, supabase_url: str, anon_key: str, client: Optional[httpx.AsyncClient] = None):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key
        self.client = client

    # Construye las cabeceras necesarias para interactuar con Supabase usando
    # autenticación del usuario y retorno de representación.
    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # La inserción individual reutiliza la lógica batch para mantener una sola ruta de persistencia.
    async def insert_chunk_label(self, access_token: str, payload: Dict[str, Any]) -> dict:
        rows = await self.insert_chunk_labels_many(access_token, [payload])
        return rows[0]

    async def insert_chunk_labels_many(self, access_token: str, payloads: List[Dict[str, Any]]) -> List[dict]:
        # Si no hay etiquetas RED2 para guardar, se devuelve lista vacía sin hacer requests.
        if not payloads:
            return []

        # Endpoint PostgREST de la tabla donde se almacenan las etiquetas por chunk de RED2.
        url = f"{self.base}/rest/v1/red2_chunk_labels"
        headers = self._headers(access_token)

        client = self.client or httpx.AsyncClient(timeout=60)
        close_after = self.client is None

        # Inserta el lote de etiquetas RED2 y propaga error si la base rechaza la operación.
        try:
            r = await client.post(url, headers=headers, json=payloads)
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase error {r.status_code}: {r.text}")
            data = r.json()
            return data if isinstance(data, list) else [data]
        finally:
            if close_after:
                await client.aclose()

    # Endpoint usado para guardar o actualizar resúmenes agregados por archivo
    # aprovechando la estrategia de merge-duplicates de PostgREST.
    async def upsert_archivo_summary(self, access_token: str, payload: Dict[str, Any]) -> dict:
        url = f"{self.base}/rest/v1/red2_archivo_summary"
        headers = self._headers(access_token)
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        client = self.client or httpx.AsyncClient(timeout=60)
        close_after = self.client is None

        try:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase error {r.status_code}: {r.text}")
            data = r.json()
            return data[0] if isinstance(data, list) and data else data
        finally:
            if close_after:
                await client.aclose()

    # Consulta una vista o tabla de lookup para recuperar etiquetas RED2 asociadas
    # a un conjunto de embeddings ya identificados por id.
    async def fetch_chunk_labels_by_embedding_ids(self, access_token: str, embedding_ids: List[str]) -> list:
        if not embedding_ids:
            return []

        ids = ",".join(str(x) for x in embedding_ids)

        url = f"{self.base}/rest/v1/red2_chunk_labels_lookup"
        params = {
            "select": "embedding_texto_id, red2_top, red2_probs, metadatos",
            "embedding_texto_id": f"in.({ids})",
        }

        client = self.client or httpx.AsyncClient(timeout=60)
        close_after = self.client is None

        try:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase error {r.status_code}: {r.text}")
            return r.json()
        finally:
            if close_after:
                await client.aclose()