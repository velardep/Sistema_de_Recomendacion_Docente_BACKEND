import httpx

class TextosEspacioRepo:
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

    async def crear(self, access_token: str, payload: dict):
        url = f"{self.base}/rest/v1/textos_espacio"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, headers=self._headers(access_token), json=payload)
            r.raise_for_status()
            return r.json()[0]
