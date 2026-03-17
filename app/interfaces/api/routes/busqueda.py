# app/interfaces/api/routes/busqueda.py

# Este archivo define la ruta de la API para búsqueda semántica.
# Permite realizar búsquedas basadas en significado de texto, utilizando embeddings.
# Incluye una función utilitaria para extraer tokens Bearer de headers de autorización.
# Forma parte del sistema de búsqueda inteligente integrado con modelos de IA.

# Framework - FastAPI
from fastapi import APIRouter, Depends, Header, HTTPException

# Interfaces - Esquemas de API
from app.interfaces.api.schemas.busqueda import BusquedaSemanticaRequest

# Interfaces - Dependencias
from app.interfaces.api.dependencies.busqueda_deps import get_busqueda_uc

# Aplicación - Casos de uso
from app.application.use_cases.buscar_semantico import BuscarSemanticoUseCase

# Creación del router para rutas de búsqueda con prefijo /busqueda y etiqueta busqueda.
router = APIRouter(prefix="/busqueda", tags=["busqueda"])

# Función utilitaria para extraer el token Bearer del header de autorización.
# Valida que el header exista y comience con "Bearer", luego extrae el token.
def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Use: Bearer <token>")
    return authorization.split(" ", 1)[1].strip()

# Endpoint POST para búsqueda semántica.
# Recibe datos de búsqueda, header de autorización y ejecuta el caso de uso con parámetros.
@router.post("/semantica")
async def busqueda_semantica(
    req: BusquedaSemanticaRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: BuscarSemanticoUseCase = Depends(get_busqueda_uc),
):
    # Extrae el token Bearer del header de autorización.
    token = extract_bearer_token(authorization)
    # Ejecuta el caso de uso con token, texto, top_k, tipo de fuente y ID del espacio.
    return await uc.execute(token, req.texto, req.top_k, req.tipo_fuente, req.espacio_id)
