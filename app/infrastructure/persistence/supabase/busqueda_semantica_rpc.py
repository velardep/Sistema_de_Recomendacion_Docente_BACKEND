import httpx

class BusquedaSemanticaRPC:
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _vector_literal(vec: list[float]) -> str:
        # pgvector acepta formato: [0.1,0.2,...]
        return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

    async def buscar(self, access_token: str, query_vec: list[float], top_k: int,
                     tipo_fuente: str | None, espacio_id: str | None, docente_id: str | None):
        url = f"{self.base}/rest/v1/rpc/buscar_semantico"
        payload = {
            "query_embedding": self._vector_literal(query_vec),
            "match_count": top_k,
            "filtro_tipo_fuente": tipo_fuente,
            "filtro_espacio_id": espacio_id,
            "filtro_docente_id": docente_id,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=self._headers(access_token), json=payload)
            r.raise_for_status()
            return r.json()
