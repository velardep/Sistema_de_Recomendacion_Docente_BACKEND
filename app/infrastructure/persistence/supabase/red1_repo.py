## app/infrastructure/persistence/supabase/red1_repo.py

# Repositorio de persistencia encargado de guardar inferencias generadas por
# RED1 en Supabase. Soporta inserción individual y por lotes, manteniendo el
# criterio de no romper el flujo principal si la persistencia falla.
from __future__ import annotations

import httpx
from typing import Any, Dict, Optional, List

# Este adapter escribe resultados de RED1 en la tabla `red1_inferencias`
# mediante PostgREST.
class Red1RepoPostgrest:
    def __init__(self, supabase_url: str, supabase_anon_key: str, client: Optional[httpx.AsyncClient] = None):
        self.base_url = supabase_url.rstrip("/")
        self.key = supabase_anon_key
        self.client = client

    # Construye las cabeceras necesarias para insertar datos en Supabase y obtener
    # de vuelta la representación de las filas insertadas.
    def _headers(self, access_token: str) -> Dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # La inserción individual reutiliza la lógica batch para mantener una única vía de persistencia.
    async def insertar_inferencia(self, access_token: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rows = await self.insertar_inferencias_many(access_token, [payload])
        return rows[0] if rows else None

    async def insertar_inferencias_many(self, access_token: str, payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Si no hay inferencias para guardar, no se realiza ninguna llamada a la base de datos.
        if not payloads:
            return []

        # Endpoint PostgREST de la tabla de inferencias RED1, se pide devolver las filas insertadas.
        url = f"{self.base_url}/rest/v1/red1_inferencias"
        params = {"select": "*"}  # devolver filas insertadas

        # Usa cliente compartido si existe en caso contrario crea uno temporal para esta operación.
        client = self.client or httpx.AsyncClient(timeout=30)
        close_after = self.client is None

        try:
            # Si el insert falla, este repositorio devuelve lista vacía para respetar la
            # política best-effort definida por el flujo de RED1.
            r = await client.post(url, headers=self._headers(access_token), params=params, json=payloads)
            if r.status_code >= 300:
                return []
            data = r.json()
            return data if isinstance(data, list) else [data]
        finally:
            if close_after:
                await client.aclose()