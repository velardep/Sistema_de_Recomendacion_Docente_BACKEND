import httpx

class RecomendacionRepositoryPostgrest:
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def crear_recomendacion(self, access_token: str, payload: dict):
        url = f"{self.base}/rest/v1/recomendaciones"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]

    async def listar_recomendaciones(self, access_token: str):
        url = f"{self.base}/rest/v1/recomendaciones"
        params = {"select": "*", "order": "created_at.desc"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            return r.json()

    async def obtener_recomendacion(self, access_token: str, recomendacion_id: str):
        url = f"{self.base}/rest/v1/recomendaciones"
        params = {"select": "*", "id": f"eq.{recomendacion_id}"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

    async def crear_accion(self, access_token: str, payload: dict):
        url = f"{self.base}/rest/v1/acciones_docente"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]

    async def listar_acciones(self, access_token: str, recomendacion_id: str):
        url = f"{self.base}/rest/v1/acciones_docente"
        params = {"select": "*", "recomendacion_id": f"eq.{recomendacion_id}", "order": "created_at.asc"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            return r.json()
