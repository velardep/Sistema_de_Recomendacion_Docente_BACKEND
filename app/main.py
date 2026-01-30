from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ✅ 1) Crear UNA sola app (con title/version desde el inicio)
app = FastAPI(title="API Taller", version="0.1.0")

# ✅ 2) Configurar CORS sobre ESA MISMA app
origins = [
    "http://localhost:5173",  # Vite
    "http://127.0.0.1:5173",
    "http://localhost:3000",  # CRA
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # incluye OPTIONS
    allow_headers=["*"],   # Authorization, Content-Type, etc.
)

# ✅ 3) Importar e incluir routers (todo igual, pero SIN redefinir app)
from app.interfaces.api.routes.health import router as health_router
from app.interfaces.api.routes.auth import router as auth_router
from app.interfaces.api.routes.me import router as me_router
from app.interfaces.api.routes.chat import router as chat_router
from app.interfaces.api.routes.recomendaciones import router as recomendaciones_router
from app.interfaces.api.routes.busqueda import router as busqueda_router
from app.interfaces.api.routes.espacios import router as espacios_router
from app.interfaces.api.routes.busqueda_mixta import router as busqueda_mixta_router
from app.interfaces.api.routes.chat_espacios import router as chat_espacios_router

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(chat_router)
app.include_router(recomendaciones_router)
app.include_router(busqueda_router)
app.include_router(espacios_router)
app.include_router(busqueda_mixta_router)
app.include_router(chat_espacios_router)



