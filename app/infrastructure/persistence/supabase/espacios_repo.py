# app/infrastructure/persistence/supabase/espacios_repo.py

# Repositorio de persistencia encargado de manejar la tabla de espacios en
# Supabase. Permite crear, listar, obtener, actualizar y eliminar espacios
# de trabajo asociados al docente.

import httpx

# Este adapter conecta los use cases de espacios con la tabla `espacios`
# expuesta por PostgREST en Supabase.
class EspaciosRepo:
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    # Construye las cabeceras HTTP necesarias para operar sobre espacios en Supabase
    # usando el token del usuario autenticado.
    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # Endpoint PostgREST de la tabla de espacios para crear un nuevo registro.
    async def crear(self, access_token: str, payload: dict):
        url = f"{self.base}/rest/v1/espacios"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, headers=self._headers(access_token), json=payload)
            r.raise_for_status()
            return r.json()[0]

    # Recupera todos los espacios visibles para el usuario autenticado según RLS.
    async def listar(self, access_token: str):
        url = f"{self.base}/rest/v1/espacios?select=*"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url, headers=self._headers(access_token))
            r.raise_for_status()
            return r.json()

    # Busca un espacio específico por id y devuelve la primera fila encontrada.
    async def obtener(self, access_token: str, espacio_id: str):
        url = f"{self.base}/rest/v1/espacios?select=*&id=eq.{espacio_id}"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url, headers=self._headers(access_token))
            r.raise_for_status()
            rows = r.json()
            return rows[0] if rows else None

    # Aplica una actualización parcial sobre el espacio indicado.
    async def actualizar(self, access_token: str, espacio_id: str, payload: dict):
        url = f"{self.base}/rest/v1/espacios?id=eq.{espacio_id}"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.patch(url, headers=self._headers(access_token), json=payload)
            r.raise_for_status()
            rows = r.json()
            return rows[0] if rows else None

    # Elimina el espacio solicitado desde la tabla de espacios.
    async def eliminar(self, access_token: str, espacio_id: str):
        url = f"{self.base}/rest/v1/espacios?id=eq.{espacio_id}"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.delete(url, headers=self._headers(access_token))
            r.raise_for_status()
            return {"ok": True}
