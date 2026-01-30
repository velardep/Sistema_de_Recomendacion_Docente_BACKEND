import httpx

from typing import Any, Dict


class EmbeddingsRepo:
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _to_pgvector_literal(self, vec: Any) -> Any:
        """
        Si tu EmbeddingsModel devuelve list[float], convertimos a "[...]" para PostgREST.
        Si ya devuelve string estilo "[...]" lo dejamos.
        """
        if isinstance(vec, str):
            return vec
        if isinstance(vec, list) or isinstance(vec, tuple):
            return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"
        return vec

    async def insert_embedding(self, access_token: str, payload: Dict[str, Any]) -> dict:
        url = f"{self.base}/rest/v1/embeddings_texto"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"

        safe = dict(payload)
        safe["embedding"] = self._to_pgvector_literal(safe.get("embedding"))

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=safe)
            if r.status_code >= 400:
                # 👇 esto te imprime el error real de Supabase/PostgREST
                raise RuntimeError(f"Supabase error {r.status_code}: {r.text}")

            return r.json()[0]
