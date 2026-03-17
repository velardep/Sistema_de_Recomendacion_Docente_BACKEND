# app/infrastructure/persistence/supabase/embeddings_repo.py

# Repositorio de persistencia encargado de insertar embeddings de texto en
# Supabase. Soporta inserción individual y por lotes para mejorar rendimiento
# en flujos de ingesta y procesamiento masivo.

import httpx
from typing import Any, Dict, List, Optional

# Este repositorio abstrae la escritura sobre la tabla de embeddings y maneja
# la conversión del vector al formato esperado por pgvector/PostgREST.
class EmbeddingsRepo:
    def __init__(self, supabase_url: str, anon_key: str, client: Optional[httpx.AsyncClient] = None):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key
        self.client = client  

    # Construye las cabeceras HTTP necesarias para escribir en Supabase con
    # autenticación del usuario y retorno de la fila insertada.
    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # Convierte el embedding al formato literal esperado por pgvector cuando
    # el vector llega como lista o tupla de floats.
    def _to_pgvector_literal(self, vec: Any) -> Any:
        if isinstance(vec, str):
            return vec
        if isinstance(vec, (list, tuple)):
            return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"
        return vec

    # La inserción individual reutiliza internamente la lógica batch para mantener
    # un único camino de persistencia.
    async def insert_embedding(self, access_token: str, payload: Dict[str, Any]) -> dict:
        rows = await self.insert_many_embeddings(access_token, [payload])
        return rows[0]

    async def insert_many_embeddings(self, access_token: str, payloads: List[Dict[str, Any]]) -> List[dict]:
        
        # Inserta N embeddings en 1 request.
        # Si no hay payloads para insertar, devuelve lista vacía sin realizar requests.
        if not payloads:
            return []

        # Endpoint PostgREST de la tabla donde se almacenan los embeddings del sistema.
        url = f"{self.base}/rest/v1/embeddings_texto"
        headers = self._headers(access_token)

        # Normaliza cada fila antes del insert para asegurar que el campo embedding
        # viaje en un formato compatible con la base de datos.
        safe_rows: List[Dict[str, Any]] = []
        for p in payloads:
            safe = dict(p)
            safe["embedding"] = self._to_pgvector_literal(safe.get("embedding"))
            safe_rows.append(safe)

        # Usa un cliente compartido si fue inyectado, si no, crea uno temporal
        # únicamente para esta operación.
        client = self.client or httpx.AsyncClient(timeout=60)  # fallback
        close_after = self.client is None

        # Ejecuta el insert batch en Supabase y propaga error si la operación falla.
        try:
            r = await client.post(url, headers=headers, json=safe_rows)
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase error {r.status_code}: {r.text}")

            data = r.json()
            return data if isinstance(data, list) else [data]
        finally:
            if close_after:
                await client.aclose()