# app/infrastructure/persistence/supabase/chat_espacios_repo.py
import httpx
from typing import Optional

class ChatEspaciosRepo:
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    # ✅ ESTE ES EL MÉTODO QUE TE FALTABA (tu use case lo llama)
    async def crear_conversacion(self, access_token: str, espacio_id: str, docente_id: str, titulo: Optional[str]):
        url = f"{self.base}/rest/v1/conversaciones_espacio"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"

        payload = {
            "espacio_id": espacio_id,
            "docente_id": docente_id,
            "titulo": titulo,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]

    async def listar_conversaciones(self, access_token: str, espacio_id: str):
        url = f"{self.base}/rest/v1/conversaciones_espacio"
        params = {
            "select": "*",
            "espacio_id": f"eq.{espacio_id}",
            "order": "created_at.desc",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            return r.json()

    async def obtener_conversacion(self, access_token: str, conversacion_espacio_id: str):
        url = f"{self.base}/rest/v1/conversaciones_espacio"
        params = {"select": "*", "id": f"eq.{conversacion_espacio_id}"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

    async def listar_mensajes(self, access_token: str, conversacion_espacio_id: str):
        url = f"{self.base}/rest/v1/mensajes_espacio"
        params = {
            "select": "*",
            "conversacion_espacio_id": f"eq.{conversacion_espacio_id}",
            "order": "created_at.asc",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            return r.json()


    async def actualizar_titulo_conversacion(
        self,
        access_token: str,
        conversacion_espacio_id: str,
        titulo: str,
    ):
        url = f"{self.base}/rest/v1/conversaciones_espacio"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"

        params = {"id": f"eq.{conversacion_espacio_id}"}
        payload = {"titulo": titulo}

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.patch(url, headers=headers, params=params, json=payload)
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None



    async def insertar_mensaje(
        self,
        *,
        access_token: str,
        conversacion_espacio_id: str,
        docente_id: str,
        rol: str,
        contenido: str,
        metadatos: dict | None = None,
    ):
        url = f"{self.base}/rest/v1/mensajes_espacio"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"

        payload = {
            "conversacion_espacio_id": conversacion_espacio_id,
            "docente_id": docente_id,
            "rol": rol,
            "contenido": contenido,
            "metadatos": metadatos or {},
        }

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]
        
    

  


        # ✅ Alias defensivo (por compatibilidad)
    async def crear_conversacion_espacio(
        self,
        access_token: str,
        espacio_id: str,
        docente_id: str,
        titulo: Optional[str],
    ):
        return await self.crear_conversacion(access_token, espacio_id, docente_id, titulo)
