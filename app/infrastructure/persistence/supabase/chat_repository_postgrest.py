# app/infrastructure/persistence/supabase/chat_repository_postgrest.py

# Repositorio de persistencia encargado de manejar conversaciones y mensajes
# del chat general en Supabase. Permite crear chats, listarlos, recuperar
# historial, actualizar títulos y registrar mensajes del usuario o assistant.

import httpx
from typing import Optional

# Este adapter conecta los flujos de chat general con las tablas
# `conversations` y `messages` en Supabase.
class ChatRepositoryPostgrest:
    # Inicializa el repositorio con la URL de Supabase y la clave anónima
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key


    # Método privado que genera los headers necesarios para las peticiones autenticadas
    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    # Crea una nueva conversación en la base de datos con el docente y título dados
    async def create_conversation(self, access_token: str, docente_id: str, titulo: Optional[str]):
        url = f"{self.base}/rest/v1/conversations"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"
        payload = {"docente_id": docente_id, "titulo": titulo}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]

    # Lista todas las conversaciones ordenadas por fecha de creación descendente
    async def list_conversations(self, access_token: str):
        url = f"{self.base}/rest/v1/conversations"
        params = {"select": "*", "order": "created_at.desc"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            return r.json()

    # Obtiene una conversación específica por su ID
    async def get_conversation(self, access_token: str, conversation_id: str):
        url = f"{self.base}/rest/v1/conversations"
        params = {"select": "*", "id": f"eq.{conversation_id}"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

    # Actualiza el título de una conversación específica
    async def update_conversation_title(self, access_token: str, conversation_id: str, titulo: str):
        url = f"{self.base}/rest/v1/conversations"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"
        params = {"id": f"eq.{conversation_id}"}
        payload = {"titulo": titulo}

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.patch(url, headers=headers, params=params, json=payload)
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

    # Lista todos los mensajes de una conversación ordenados por fecha ascendente
    async def list_messages(self, access_token: str, conversation_id: str):
        url = f"{self.base}/rest/v1/messages"
        params = {"select": "*", "conversation_id": f"eq.{conversation_id}", "order": "created_at.asc"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            return r.json()

    # Inserta un nuevo mensaje en la conversación con rol, contenido y metadatos
    async def insert_message(
        self,
        access_token: str,
        conversation_id: str,
        docente_id: str,
        role: str,
        content: str,
        meta: dict | None = None,
    ) -> dict:
        url = f"{self.base}/rest/v1/messages"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"

        # Prepara los datos del mensaje a insertar
        payload = {
            "conversation_id": conversation_id,
            "docente_id": docente_id,
            "role": role,
            "content": content,
            "meta": meta or {},
        }

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]

    # Obtiene el historial de mensajes de una conversación en formato simplificado
    async def get_history(self, access_token: str, conversation_id: str) -> list[dict]:
        rows = await self.list_messages(access_token, conversation_id)
        return [{"role": m.get("role"), "content": m.get("content")} for m in rows]


# Función que determina si un título de conversación es genérico o no
def is_generic_title(titulo: str | None) -> bool:
    # Si no hay título, se considera genérico
    if not titulo:
        return True
    # Normaliza el título para comparación
    t = titulo.strip().lower()
    # Define una lista de títulos considerados genéricos
    genericos = {
        "chat", "nuevo chat", "conversación", "conversacion",
        "chat general", "chat de espacio", "chat espacio",
    }
    # Verifica si el título normalizado está en la lista
    if t in genericos:
        return True
    # Verifica si el título comienza con frases predeterminadas, permitiendo sufijos
    if t.startswith("chat general"):
        return True
    if t.startswith("chat de espacio"):
        return True
    if t.startswith("chat espacio"):
        return True
    return False

