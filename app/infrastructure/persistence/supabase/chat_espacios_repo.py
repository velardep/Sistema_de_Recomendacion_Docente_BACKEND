# app/infrastructure/persistence/supabase/chat_espacios_repo.py

# Repositorio de persistencia encargado de manejar conversaciones y mensajes
# del chat por espacios en Supabase. Permite crear conversaciones, listarlas,
# obtener una conversación específica, actualizar su título y registrar mensajes.

import httpx
from typing import Optional

# Este adapter conecta los flujos de chat por espacio con las tablas
# `conversaciones_espacio` y `mensajes_espacio` en Supabase.
class ChatEspaciosRepo:
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    # Construye las cabeceras HTTP necesarias para autenticar y ejecutar operaciones
    # sobre las tablas del chat de espacios en Supabase.
    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    # Endpoint PostgREST de la tabla de conversaciones por espacio, se pide que
    # Supabase devuelva la fila insertada.
    async def crear_conversacion(self, access_token: str, espacio_id: str, docente_id: str, titulo: Optional[str]):
        url = f"{self.base}/rest/v1/conversaciones_espacio"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"

        # Datos mínimos necesarios para crear una nueva conversación asociada a un espacio.
        payload = {
            "espacio_id": espacio_id,
            "docente_id": docente_id,
            "titulo": titulo,
        }

        # Inserta la conversación en Supabase y devuelve la fila creada.
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]

    # Recupera todas las conversaciones del espacio solicitado, ordenadas de la más reciente a la más antigua.
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

    # Busca una conversación específica de espacio por su identificador único.
    async def obtener_conversacion(self, access_token: str, conversacion_espacio_id: str):
        url = f"{self.base}/rest/v1/conversaciones_espacio"
        params = {"select": "*", "id": f"eq.{conversacion_espacio_id}"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

    # Recupera el historial completo de mensajes de una conversación de espacio
    # en orden cronológico ascendente.
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

    # Actualiza el título de una conversación de espacio y devuelve la fila resultante.
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

    # Endpoint de la tabla de mensajes del chat por espacios.
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

        # Estructura del mensaje que se almacenará, incluyendo rol y metadatos opcionales.
        payload = {
            "conversacion_espacio_id": conversacion_espacio_id,
            "docente_id": docente_id,
            "rol": rol,
            "contenido": contenido,
            "metadatos": metadatos or {},
        }

        # Inserta el mensaje en la conversación y devuelve la fila creada.
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]
        
    # Alias de compatibilidad mantenido para no romper flujos antiguos o llamadas
    # previas que todavía usen este nombre de método.
    async def crear_conversacion_espacio(
        self,
        access_token: str,
        espacio_id: str,
        docente_id: str,
        titulo: Optional[str],
    ):
        return await self.crear_conversacion(access_token, espacio_id, docente_id, titulo)
