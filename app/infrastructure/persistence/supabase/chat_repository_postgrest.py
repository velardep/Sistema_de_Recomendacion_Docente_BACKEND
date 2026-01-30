# app/infrastructure/persistence/supabase/chat_repository_postgrest.py
import httpx
from typing import Optional


class ChatRepositoryPostgrest:
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def create_conversation(self, access_token: str, docente_id: str, titulo: Optional[str]):
        url = f"{self.base}/rest/v1/conversations"
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"
        payload = {"docente_id": docente_id, "titulo": titulo}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()[0]

    async def list_conversations(self, access_token: str):
        url = f"{self.base}/rest/v1/conversations"
        params = {"select": "*", "order": "created_at.desc"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            return r.json()

    async def get_conversation(self, access_token: str, conversation_id: str):
        url = f"{self.base}/rest/v1/conversations"
        params = {"select": "*", "id": f"eq.{conversation_id}"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

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

    async def list_messages(self, access_token: str, conversation_id: str):
        url = f"{self.base}/rest/v1/messages"
        params = {"select": "*", "conversation_id": f"eq.{conversation_id}", "order": "created_at.asc"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            r.raise_for_status()
            return r.json()

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

    async def get_history(self, access_token: str, conversation_id: str) -> list[dict]:
        rows = await self.list_messages(access_token, conversation_id)
        return [{"role": m.get("role"), "content": m.get("content")} for m in rows]


def is_generic_title(titulo: str | None) -> bool:
    if not titulo:
        return True
    t = titulo.strip().lower()
    return t in {"chat general"} or t.startswith("chat general ")
