import httpx

class RecomendacionesEspacioRepo:
    """
    Repo PostgREST para tabla: recomendaciones_espacio (o el nombre real que tengas).
    OJO: si tu tabla se llama distinto, cambia TABLE abajo.
    """

    TABLE = "recomendaciones_espacio"  # <- si tu tabla se llama diferente, ajusta aquí

    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def crear_recomendacion_espacio(self, access_token: str, payload: dict) -> dict:
        url = f"{self.base}/rest/v1/{self.TABLE}"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]
