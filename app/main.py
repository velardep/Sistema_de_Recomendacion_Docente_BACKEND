from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.ai.ensure_models import ensure_models_downloaded

# Handlers globales para errores upstream (Supabase)
from fastapi import Request
from fastapi.responses import JSONResponse
import httpx

#import logging
#logging.basicConfig(level=logging.DEBUG)

import logging
import re

class RedactSecretsFilter(logging.Filter):
    # Bearer <token>
    BEARER_RE = re.compile(r"(Authorization:\s*Bearer\s+)[^\s]+", re.IGNORECASE)
    # apikey: <token> (Supabase suele usar apikey header)
    APIKEY_RE = re.compile(r"(apikey:\s*)[^\s]+", re.IGNORECASE)
    # también por si aparece como JSON/strings
    BEARER_INLINE_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9\-\._~\+/]+=*", re.IGNORECASE)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        msg = self.BEARER_RE.sub(r"\1<REDACTED>", msg)
        msg = self.APIKEY_RE.sub(r"\1<REDACTED>", msg)
        msg = self.BEARER_INLINE_RE.sub(r"\1<REDACTED>", msg)
        record.msg = msg
        record.args = ()
        return True

# Mantienes DEBUG global para tu app
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# Redacta secretos en TODOS los logs (incluye httpx/httpcore si imprimen headers)
logging.getLogger().addFilter(RedactSecretsFilter())

# Mantén debug útil, pero evita que httpcore/hpack te escupa headers sensibles
logging.getLogger("httpcore").setLevel(logging.INFO)  # o WARNING si sigue ruidoso
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.INFO)

# Crear UNA sola app (con title/version desde el inicio)
app = FastAPI(title="API Taller", version="0.1.0")

# Asegurarse de que los modelos estén descargados al iniciar la app (antes de recibir requests)
ensure_models_downloaded()


# Handler global para cuando Supabase responde 4xx/5xx y httpx lanza HTTPStatusError
@app.exception_handler(httpx.HTTPStatusError)
async def httpx_status_error_handler(request: Request, exc: httpx.HTTPStatusError):
    status = exc.response.status_code

    # intentamos devolver el detalle real (json) y si no, texto
    try:
        detail = exc.response.json()
    except Exception:
        detail = exc.response.text

    return JSONResponse(
        status_code=status,
        content={"detail": detail},
    )

# Handler global para errores de red/timeout hacia Supabase
@app.exception_handler(httpx.RequestError)
async def httpx_request_error_handler(request: Request, exc: httpx.RequestError):
    # 502 Bad Gateway: tu API está bien, el upstream (Supabase) falló
    return JSONResponse(
        status_code=502,
        content={"detail": "Upstream error contacting Supabase", "error": str(exc)},
    )

# Configurar CORS sobre ESA MISMA app
origins = [
    "http://localhost:5173",  # Vite
    "http://127.0.0.1:5173",
    "http://localhost:3000",  # CRA
    "http://127.0.0.1:3000",
    "https://frontend-sipre.velardep44.workers.dev",
    "https://sistema-de-recomendacion-docente-frontend.pages.dev"

    
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # incluye OPTIONS
    allow_headers=["*"],   # Authorization, Content-Type, etc.
)

# Importar e incluir routers (todo igual, pero SIN redefinir app)
from app.interfaces.api.routes.health import router as health_router
from app.interfaces.api.routes.auth import router as auth_router
from app.interfaces.api.routes.me import router as me_router
from app.interfaces.api.routes.chat import router as chat_router
from app.interfaces.api.routes.busqueda import router as busqueda_router
from app.interfaces.api.routes.espacios import router as espacios_router
from app.interfaces.api.routes.busqueda_mixta import router as busqueda_mixta_router
from app.interfaces.api.routes.chat_espacios import router as chat_espacios_router
from app.interfaces.api.routes.pdc import router as pdc_router
from app.interfaces.api.routes.pdc_library import router as pdc_library_router
from app.interfaces.api.routes.red3 import router as red3_router
from app.debug_httpx_caller import install as install_httpx_tracer
install_httpx_tracer()


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(chat_router)
app.include_router(busqueda_router)
app.include_router(espacios_router)
app.include_router(busqueda_mixta_router)
app.include_router(chat_espacios_router)
app.include_router(pdc_router)
app.include_router(pdc_library_router)
app.include_router(red3_router)

