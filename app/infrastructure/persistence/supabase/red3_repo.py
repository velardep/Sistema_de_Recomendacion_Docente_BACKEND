# app/infrastructure/persistence/supabase/red3_repo.py

# Repositorio de persistencia encargado de manejar los datos operativos de RED3:
# eventos del docente, ejecución de snapshots, lectura de snapshots recientes y
# almacenamiento del perfil adaptativo del usuario.
from __future__ import annotations

import httpx

from typing import Any, Dict, Optional

# Este adapter concentra la comunicación entre la capa de aplicación RED3
# y las tablas/RPCs de Supabase que sostienen el monitoreo adaptativo.
    # insert events into public.red3_docente_events
    # call RPC public.red3_upsert_snapshots_7d_30d
    # read latest snapshot from public.red3_docente_feature_snapshots
    # upsert style profile into public.red3_docente_style_profiles
class Red3RepoPostgrest:
    def __init__(
        self,
        supabase_url: str,
        supabase_anon_key: str,
        client: Optional[httpx.AsyncClient] = None,  # ✅ NUEVO: pool compartido
    ):
        self.base = supabase_url.rstrip("/")
        self.key = supabase_anon_key
        self._client = client  

    # Construye las cabeceras HTTP necesarias para interactuar con Supabase
    # usando el token del usuario autenticado.
    def _headers(self, access_token: str) -> Dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # Endpoint PostgREST de la tabla donde se registran eventos de actividad del docente.
    async def insert_event(self, access_token: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base}/rest/v1/red3_docente_events"

        # Inserta el evento usando cliente compartido si existe; en caso contrario
        # crea un cliente temporal para esta operación.
        if self._client is not None:
            r = await self._client.post(url, headers=self._headers(access_token), json=payload)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers=self._headers(access_token), json=payload)

        # Si la inserción falla, devuelve None para que la capa superior pueda tratarlo como best-effort.
        if r.status_code >= 300:
            return None
        data = r.json()
        return data[0] if isinstance(data, list) and data else data

    # Llama a la RPC que recalcula o actualiza snapshots agregados de 7 y 30 días
    # para el docente indicado: red3_upsert_snapshots_7d_30d(docente_id uuid, period_end date)
    # period_end: 'YYYY-MM-DD'
    async def run_snapshots(self, access_token: str, docente_id: str, period_end: str) -> bool:
        url = f"{self.base}/rest/v1/rpc/red3_upsert_snapshots_7d_30d"
        body = {"p_docente_id": docente_id, "p_period_end": period_end}

        if self._client is not None:
            r = await self._client.post(url, headers=self._headers(access_token), json=body)
        else:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(url, headers=self._headers(access_token), json=body)

        return r.status_code < 300

    async def get_latest_snapshot(
        self,
        access_token: str,
        docente_id: str,
        window_days: int = 30,
    ) -> Optional[Dict[str, Any]]:
        # Recupera el snapshot más reciente de la ventana solicitada para ese docente (7 o 30).
        url = f"{self.base}/rest/v1/red3_docente_feature_snapshots"
        params = {
            "select": "*",
            "docente_id": f"eq.{docente_id}",
            "window_days": f"eq.{int(window_days)}",
            "order": "period_end.desc",
            "limit": "1",
        }

        if self._client is not None:
            r = await self._client.get(url, headers=self._headers(access_token), params=params)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers(access_token), params=params)

        if r.status_code >= 300:
            return None
        rows = r.json()
        return rows[0] if isinstance(rows, list) and rows else None

    # Endpoint de perfiles RED3. Usa merge-duplicates para actualizar o insertar
    # el perfil adaptativo según exista o no una fila previa.
    async def upsert_style_profile(self, access_token: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base}/rest/v1/red3_docente_style_profiles"
        headers = self._headers(access_token).copy()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        if self._client is not None:
            r = await self._client.post(url, headers=headers, json=payload)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers=headers, json=payload)

        if r.status_code >= 300:
            return None
        data = r.json()
        return data[0] if isinstance(data, list) and data else data

    # Recupera el perfil RED3 actual del docente si ya fue calculado y almacenado.
    async def get_style_profile(self, access_token: str, docente_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base}/rest/v1/red3_docente_style_profiles"
        params = {"select": "*", "docente_id": f"eq.{docente_id}", "limit": "1"}

        if self._client is not None:
            r = await self._client.get(url, headers=self._headers(access_token), params=params)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers(access_token), params=params)

        if r.status_code >= 300:
            return None
        rows = r.json()
        return rows[0] if isinstance(rows, list) and rows else None