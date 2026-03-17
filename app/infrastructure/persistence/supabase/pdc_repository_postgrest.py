# app/infrastructure/persistence/supabase/pdc_repository_postgrest.py

# Repositorio de persistencia encargado de guardar la trazabilidad completa del
# flujo de generación de PDC en Supabase. Maneja el registro del request, las
# influencias utilizadas, el documento generado y la ejecución técnica del proceso.

import httpx
from typing import Dict, Any

# Este adapter conecta la generación de PDC con las tablas `pdc_requests`,
# `pdc_influences`, `pdc_documents` y `pdc_runs` en Supabase.
class PdcRepositoryPostgrest:
    # Inicializa el repositorio con la URL y clave de Supabase
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    # Método privado que genera los headers para autenticación y representación
    def _headers(self, access_token: str) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # Crea un registro de solicitud de PDC con el docente y payload
    async def create_request(self, access_token: str, docente_id: str, payload: Dict[str, Any]) -> str:
        url = f"{self.base}/rest/v1/pdc_requests"
        body = {"docente_id": docente_id, "payload": payload}

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=self._headers(access_token), json=body)
            r.raise_for_status()
            return r.json()[0]["id"]

    # Crea un registro de influencias utilizadas en la generación del PDC
    async def create_influences(
        self,
        access_token: str,
        pdc_request_id: str,
        docente_id: str,
        red1: Dict[str, Any],
        red2: Dict[str, Any],
        prontuario: Dict[str, Any],
    ) -> str:
        url = f"{self.base}/rest/v1/pdc_influences"
        # Prepara el cuerpo con las influencias de las redes y prontuario
        body = {
            "pdc_request_id": pdc_request_id,
            "docente_id": docente_id,
            "red1": red1,
            "red2": red2,
            "prontuario": prontuario,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=self._headers(access_token), json=body)
            r.raise_for_status()
            return r.json()[0]["id"]

    # Crea un registro del documento PDC generado
    async def create_document(
        self,
        access_token: str,
        pdc_request_id: str,
        docente_id: str,
        titulo: str,
        generado: Dict[str, Any],
    ) -> str:
        url = f"{self.base}/rest/v1/pdc_documents"
        body = {
            "pdc_request_id": pdc_request_id,
            "docente_id": docente_id,
            "titulo": titulo,
            "generado": generado,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=self._headers(access_token), json=body)
            r.raise_for_status()
            return r.json()[0]["id"]

    # Crea un registro de la ejecución del proceso de PDC con estado y metadatos
    async def create_run(
        self,
        access_token: str,
        pdc_document_id: str,
        docente_id: str,
        status: str,
        meta: Dict[str, Any],
        error: str | None = None,
    ) -> str:
        url = f"{self.base}/rest/v1/pdc_runs"
        # Prepara el cuerpo con el estado, metadatos y error opcional
        body = {
            "pdc_document_id": pdc_document_id,
            "docente_id": docente_id,
            "status": status,
            "meta": meta,
            "error": error,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=self._headers(access_token), json=body)
            r.raise_for_status()
            return r.json()[0]["id"]