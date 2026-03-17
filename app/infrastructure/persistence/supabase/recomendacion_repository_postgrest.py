# app/infrastructure/persistence/supabase/recomendacion_repository_postgrest.py

# Repositorio de persistencia encargado de manejar recomendaciones almacenadas
# en Supabase. Permite crear recomendaciones nuevas, listarlas y recuperar
# una recomendación específica por su identificador.
import httpx

# Este adapter conecta la capa de aplicación con la tabla `recomendaciones`
# usada para registrar sugerencias generadas por el sistema.
class RecomendacionRepositoryPostgrest:
    # Inicializa el repositorio con la URL y clave de Supabase
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    # Método privado que genera los headers para autenticación
    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    # Crea una nueva recomendación en la base de datos
    async def crear_recomendacion(self, access_token: str, payload: dict):
        url = f"{self.base}/rest/v1/recomendaciones"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]

    # Lista todas las recomendaciones ordenadas por fecha descendente
    async def listar_recomendaciones(self, access_token: str):
        url = f"{self.base}/rest/v1/recomendaciones"
        params = {"select": "*", "order": "created_at.desc"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            return r.json()

    # Obtiene una recomendación específica por su ID
    async def obtener_recomendacion(self, access_token: str, recomendacion_id: str):
        url = f"{self.base}/rest/v1/recomendaciones"
        params = {"select": "*", "id": f"eq.{recomendacion_id}"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

