from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

import httpx


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"

class PdcLibraryRepo:
    """
    Repo aislado:
    - Guarda metadata en tabla public.pdc_library_items (RLS)
    - Guarda archivo en Storage bucket privado
    Trabaja con Bearer del usuario (igual que tu sistema).
    """

    def __init__(self, supabase_url: str, anon_key: str, bucket: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key
        self.bucket = bucket

    def _headers_json(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _headers_storage(self, access_token: str, content_type: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": content_type,
        }

    # --------------------
    # DB
    # --------------------
    async def list_items(self, access_token: str) -> List[Dict[str, Any]]:
        url = f"{self.base}/rest/v1/pdc_library_items"
        params = {"select": "*", "order": "created_at.desc"}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url, headers=self._headers_json(access_token), params=params)
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase error {r.status_code}: {r.text}")
            return r.json()

    async def insert_item(
        self,
        access_token: str,
        docente_id: str,
        original_name: str,
        storage_path: str,
        mime_type: str = DOCX_MIME,
        size_bytes: Optional[int] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base}/rest/v1/pdc_library_items"
        payload = {
            "docente_id": docente_id,
            "original_name": original_name,
            "storage_path": storage_path,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=self._headers_json(access_token), json=payload)
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase error {r.status_code}: {r.text}")
            return r.json()[0]

    async def get_item_by_id(self, access_token: str, item_id: str) -> Dict[str, Any]:
        url = f"{self.base}/rest/v1/pdc_library_items"
        params = {"select": "*", "id": f"eq.{item_id}"}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url, headers=self._headers_json(access_token), params=params)
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase error {r.status_code}: {r.text}")
            rows = r.json()
            if not rows:
                raise RuntimeError("No existe el documento (o no tienes permiso).")
            return rows[0]

    async def delete_item(self, access_token: str, item_id: str) -> Dict[str, Any]:
        # Primero obtener (para saber storage_path) — RLS asegura ownership
        it = await self.get_item_by_id(access_token, item_id)

        url = f"{self.base}/rest/v1/pdc_library_items"
        params = {"id": f"eq.{item_id}"}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.delete(url, headers=self._headers_json(access_token), params=params)
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase error {r.status_code}: {r.text}")

        return it

    # --------------------
    # STORAGE
    # --------------------
    async def upload_file(
        self,
        access_token: str,
        docente_id: str,
        filename: str,
        content: bytes,
        content_type: str = DOCX_MIME,
    ) -> str:
        # path: docente_id/<uuid>.docx
        ext = os.path.splitext(filename)[1].lower() or ".docx"
        object_name = f"{uuid.uuid4().hex}{ext}"
        storage_path = f"{docente_id}/{object_name}"

        url = f"{self.base}/storage/v1/object/{self.bucket}/{storage_path}"

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, headers=self._headers_storage(access_token, content_type), content=content)
            if r.status_code >= 400:
                raise RuntimeError(f"Storage upload error {r.status_code}: {r.text}")

        return storage_path

    async def download_file(self, access_token: str, storage_path: str) -> bytes:
        # GET /storage/v1/object/authenticated/<bucket>/<path>
        url = f"{self.base}/storage/v1/object/authenticated/{self.bucket}/{storage_path}"

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.get(url, headers={"apikey": self.anon_key, "Authorization": f"Bearer {access_token}"})
            if r.status_code >= 400:
                raise RuntimeError(f"Storage download error {r.status_code}: {r.text}")
            return r.content

    async def delete_file(self, access_token: str, storage_path: str) -> None:
        # POST /storage/v1/object/<bucket>/remove  body: {"prefixes":["a/b.docx"]}
        url = f"{self.base}/storage/v1/object/{self.bucket}/remove"
        body = {"prefixes": [storage_path]}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=self._headers_json(access_token), json=body)
            if r.status_code >= 400:
                raise RuntimeError(f"Storage delete error {r.status_code}: {r.text}")