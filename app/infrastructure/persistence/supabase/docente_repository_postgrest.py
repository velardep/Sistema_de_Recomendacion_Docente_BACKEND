# app/infrastructure/persistence/supabase/docente_repository_postgrest.py

# Repositorio de persistencia encargado de leer y guardar el perfil del docente
# en Supabase. Permite obtener un docente por su id y hacer upsert del registro
# usando la clave primaria del usuario autenticado.
import httpx

# Clase que maneja la persistencia de docentes en Supabase
class DocenteRepositoryPostgrest:
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

    # Obtiene un docente por su ID de usuario
    async def get_by_id(self, access_token: str, user_id: str) -> dict | None:
        url = f"{self.base}/rest/v1/docentes"
        params = {"id": f"eq.{user_id}", "select": "*"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

    # Inserta o actualiza un docente en la base de datos
    async def upsert(self, access_token: str, docente: dict) -> dict:
        # upsert por pk id
        url = f"{self.base}/rest/v1/docentes"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=docente)
            r.raise_for_status()
            data = r.json()
            # Maneja el retorno: si es lista toma el primero, sino devuelve el dato
            return data[0] if isinstance(data, list) and data else data
