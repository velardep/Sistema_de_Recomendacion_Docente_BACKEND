# app/infrastructure/http/http_client.py

# Módulo de infraestructura encargado de proporcionar un cliente HTTP compartido
# basado en httpx.AsyncClient. Su objetivo es reutilizar conexiones HTTP/TLS
# y evitar crear un cliente nuevo en cada request del sistema.

from __future__ import annotations
import httpx
from typing import Optional

# Instancia global del cliente HTTP utilizada como singleton dentro de la aplicación.
# Permite reutilizar el mismo pool de conexiones en todo el backend.
_client: Optional[httpx.AsyncClient] = None

# Devuelve una instancia única de AsyncClient reutilizable en toda la aplicación.
# Si el cliente aún no existe, se crea con configuración de timeout y límites de conexión.
def get_httpx_client() -> httpx.AsyncClient:
    global _client
    # Si aún no existe una instancia del cliente HTTP, se inicializa.
    if _client is None:
        # Configuración de tiempos máximos para las distintas fases de una conexión HTTP.
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

        # Límites del pool de conexiones HTTP para controlar concurrencia y reutilización de conexiones keep-alive.
        limits = httpx.Limits(max_connections=50, max_keepalive_connections=20, keepalive_expiry=30.0)

        # Crea la instancia compartida del cliente HTTP con la configuración definida.
        _client = httpx.AsyncClient(timeout=timeout, limits=limits)

    # Devuelve la instancia singleton del cliente HTTP para ser reutilizada por repositorios o servicios.
    return _client

# Cierra explícitamente el cliente HTTP compartido cuando la aplicación se apaga,
# liberando conexiones abiertas y recursos del pool.
async def close_httpx_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None 