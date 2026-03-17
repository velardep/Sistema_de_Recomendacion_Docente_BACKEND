# app/infrastructure/persistence/supabase/red3_llm_recs_repo.py

# Repositorio de persistencia encargado de almacenar y recuperar la caché
# de recomendaciones generadas por LLM para RED3. Su objetivo es evitar
# regeneraciones innecesarias mientras la recomendación siga vigente.
from __future__ import annotations

import httpx


from typing import Any, Dict, Optional
from datetime import datetime, timezone

# Este adapter maneja una caché persistente de recomendaciones RED3 basada
# en docente, ventana temporal y fecha de corte.
# Permite leer la última recomendación válida (no expirada) y hacer upsert
class Red3LlmRecsRepoPostgrest:

    def __init__(self, supabase_url: str, supabase_anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.key = supabase_anon_key

    # Construye las cabeceras HTTP necesarias para leer y escribir la caché
    # de recomendaciones en Supabase.
    def _headers(self, access_token: str) -> Dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # Busca la recomendación más reciente todavía vigente para ese docente y
    # esa ventana temporal, usando expires_at como criterio de validez.
    async def get_latest_valid(
        self,
        access_token: str,
        docente_id: str,
        window_days: int,
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base}/rest/v1/red3_llm_recommendations"

        now_iso = datetime.now(timezone.utc).isoformat()
        params = {
            "select": "*",
            "docente_id": f"eq.{docente_id}",
            "window_days": f"eq.{int(window_days)}",
            "expires_at": f"gt.{now_iso}",
            "order": "generated_at.desc",
            "limit": "1",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=self._headers(access_token), params=params)
            if r.status_code >= 300:
                return None
            rows = r.json()
            return rows[0] if isinstance(rows, list) and rows else None

    # Inserta o actualiza la caché de recomendaciones RED3 usando la clave única
    # definida por docente, ventana temporal y fecha de corte.
    async def upsert(
        self,
        access_token: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Requiere UNIQUE(docente_id, window_days, period_end).
        """
        url = f"{self.base}/rest/v1/red3_llm_recommendations"
        headers = self._headers(access_token).copy()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code >= 300:
                return None
            data = r.json()
            return data[0] if isinstance(data, list) and data else data