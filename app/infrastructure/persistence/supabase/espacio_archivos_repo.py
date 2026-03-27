# app/infrastructure/persistence/supabase/espacio_archivos_repo.py

# Repositorio de persistencia para la tabla espacio_archivos.
# Maneja creación, listado, obtención, actualización y borrado completo
# mediante RPC del registro maestro de archivos subidos a espacios.

import httpx
from typing import Any, Dict, List, Optional


class EspacioArchivosRepo:
    def __init__(self, supabase_url: str, anon_key: str, client: Optional[httpx.AsyncClient] = None):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key
        self.client = client

    # Construye las cabeceras HTTP necesarias para operar en Supabase con
    # autenticación del usuario y retorno de representación cuando aplica.
    def _headers(self, access_token: str, prefer: str = "return=representation") -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        }

    # Inserta un registro maestro de archivo para el espacio.
    async def crear(self, access_token: str, payload: Dict[str, Any]) -> dict:
        url = f"{self.base}/rest/v1/espacio_archivos"
        client = self.client or httpx.AsyncClient(timeout=30)
        close_after = self.client is None
        try:
            r = await client.post(url, headers=self._headers(access_token), json=payload)
            r.raise_for_status()
            rows = r.json()
            return rows[0] if isinstance(rows, list) and rows else rows
        finally:
            if close_after:
                await client.aclose()

    # Lista los archivos de un espacio visibles para el usuario autenticado.
    async def listar_por_espacio(self, access_token: str, espacio_id: str) -> List[dict]:
        url = (
            f"{self.base}/rest/v1/espacio_archivos"
            f"?select=*"
            f"&espacio_id=eq.{espacio_id}"
            f"&order=created_at.desc"
        )
        client = self.client or httpx.AsyncClient(timeout=30)
        close_after = self.client is None
        try:
            r = await client.get(url, headers=self._headers(access_token))
            r.raise_for_status()
            return r.json()
        finally:
            if close_after:
                await client.aclose()

    # Obtiene un archivo específico por su id dentro de un espacio.
    async def obtener(self, access_token: str, espacio_id: str, file_id: str) -> Optional[dict]:
        url = (
            f"{self.base}/rest/v1/espacio_archivos"
            f"?select=*"
            f"&id=eq.{file_id}"
            f"&espacio_id=eq.{espacio_id}"
        )
        client = self.client or httpx.AsyncClient(timeout=30)
        close_after = self.client is None
        try:
            r = await client.get(url, headers=self._headers(access_token))
            r.raise_for_status()
            rows = r.json()
            return rows[0] if rows else None
        finally:
            if close_after:
                await client.aclose()

    # Actualiza parcialmente el registro maestro del archivo.
    async def actualizar(self, access_token: str, file_id: str, payload: Dict[str, Any]) -> Optional[dict]:
        url = f"{self.base}/rest/v1/espacio_archivos?id=eq.{file_id}"
        client = self.client or httpx.AsyncClient(timeout=30)
        close_after = self.client is None
        try:
            r = await client.patch(url, headers=self._headers(access_token), json=payload)
            r.raise_for_status()
            rows = r.json()
            return rows[0] if rows else None
        finally:
            if close_after:
                await client.aclose()

    # Ejecuta la RPC que borra el archivo del espacio y todo el procesamiento relacionado.
    async def eliminar_completo(self, access_token: str, docente_id: str, espacio_id: str, file_id: str) -> dict:
        url = f"{self.base}/rest/v1/rpc/delete_espacio_archivo_full"
        payload = {
            "p_docente_id": docente_id,
            "p_espacio_id": espacio_id,
            "p_file_id": file_id,
        }
        client = self.client or httpx.AsyncClient(timeout=60)
        close_after = self.client is None
        try:
            r = await client.post(url, headers=self._headers(access_token), json=payload)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, dict) else {"ok": False, "detail": "Respuesta RPC inválida"}
        finally:
            if close_after:
                await client.aclose()