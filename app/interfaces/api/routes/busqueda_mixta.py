# app/interfaces/api/routes/busqueda_mixta.py

# Este archivo define la ruta de la API para búsqueda mixta en espacios de trabajo.
# Permite realizar búsquedas combinadas de texto y semántica dentro de un espacio específico.
# Utiliza casos de uso para procesar la solicitud, extrayendo tokens de autorización.
# Forma parte del sistema de búsqueda avanzada integrado con embeddings y repositorios.

# Framework - FastAPI
from fastapi import APIRouter, Depends, Header

# Interfaces - Esquemas de API
from app.interfaces.api.schemas.busqueda_mixta import BusquedaMixtaRequest

# Interfaces - Dependencias
from app.interfaces.api.dependencies.busqueda_mixta_deps import get_busqueda_mixta_uc

# Interfaces - Utilidades de rutas
from app.interfaces.api.routes.busqueda import extract_bearer_token  # ya lo tienes

# Creación del router para rutas de espacios con prefijo /espacios y etiqueta busqueda-mixta.
router = APIRouter(prefix="/espacios", tags=["busqueda-mixta"])

# Endpoint POST para búsqueda mixta en un espacio específico.
# Recibe ID del espacio, datos de búsqueda, header de autorización y ejecuta el caso de uso.
@router.post("/{espacio_id}/busqueda-mixta")
async def busqueda_mixta(espacio_id: str, req: BusquedaMixtaRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_busqueda_mixta_uc)):
    # Extrae el token Bearer del header de autorización.
    token = extract_bearer_token(authorization)
    # Ejecuta el caso de uso con token, ID del espacio y datos de la solicitud.
    return await uc.execute(token, espacio_id, req.model_dump())
