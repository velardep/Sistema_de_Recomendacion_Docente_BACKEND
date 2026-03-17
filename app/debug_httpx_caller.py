# app/debug_httpx_caller.py
import httpx
import traceback
import logging

log = logging.getLogger("debug.httpx_caller")

_original_request = httpx.AsyncClient.request

async def _patched_request(self, method, url, *args, **kwargs):
    url_str = str(url)

    # Filtra solo lo que te interesa
    if "recomendaciones_espacio" in url_str:
        print("\n" + "=" * 90)
        print(f"[DEBUG] httpx.AsyncClient.request -> {method} {url_str}")
        print("[DEBUG] Caller stack (archivo:linea):")

        # Stack completo (muestra archivo y línea)
        stack = traceback.format_stack(limit=60)
        for line in stack:
            print(line.rstrip())

        print("=" * 90 + "\n")

    return await _original_request(self, method, url, *args, **kwargs)

def install():
    httpx.AsyncClient.request = _patched_request
    log.warning("Installed httpx caller tracer (AsyncClient.request patched)")