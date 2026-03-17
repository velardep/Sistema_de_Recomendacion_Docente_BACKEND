# app/interfaces/api/routes/espacios.py

# Este archivo define las rutas de la API para gestión de espacios de trabajo.
# Incluye endpoints para crear, listar, obtener, actualizar y eliminar espacios,
# además de ingestar texto en un espacio, utilizando casos de uso para la lógica.
# Maneja autenticación vía tokens Bearer y validaciones de datos.

# Framework - FastAPI
from fastapi import APIRouter, Depends, Header, HTTPException

# Interfaces - Esquemas de API
from app.interfaces.api.schemas.espacios import CrearEspacioRequest, ActualizarEspacioRequest
from app.interfaces.api.schemas.ingesta_texto import IngestarTextoRequest

# Interfaces - Utilidades de rutas
from app.interfaces.api.routes.busqueda import extract_bearer_token  # ya lo tienes

# Interfaces - Dependencias
from app.interfaces.api.dependencies.espacios_deps import (
    get_crear_espacio_uc, get_listar_espacios_uc, get_obtener_espacio_uc,
    get_actualizar_espacio_uc, get_eliminar_espacio_uc, get_ingestar_texto_uc
)

# Creación del router para rutas de espacios con prefijo /espacios y etiqueta espacios.
router = APIRouter(prefix="/espacios", tags=["espacios"])

# Endpoint POST para crear un nuevo espacio.
# Extrae token y ejecuta el caso de uso con los datos del espacio.
@router.post("")
async def crear_espacio(req: CrearEspacioRequest,
                       authorization: str | None = Header(default=None, alias="Authorization"),
                       uc=Depends(get_crear_espacio_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, req.model_dump(exclude_none=True))

# Endpoint GET para listar todos los espacios del usuario.
# Extrae token y ejecuta el caso de uso para obtener la lista.
@router.get("")
async def listar_espacios(authorization: str | None = Header(default=None, alias="Authorization"),
                          uc=Depends(get_listar_espacios_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token)

# Endpoint GET para obtener detalles de un espacio específico.
# Extrae token y ejecuta el caso de uso con el ID del espacio.
@router.get("/{espacio_id}")
async def obtener_espacio(espacio_id: str,
                          authorization: str | None = Header(default=None, alias="Authorization"),
                          uc=Depends(get_obtener_espacio_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id)

# Endpoint PATCH para actualizar un espacio.
# Extrae token, valida que haya datos para actualizar y ejecuta el caso de uso.
@router.patch("/{espacio_id}")
async def actualizar_espacio(espacio_id: str, req: ActualizarEspacioRequest,
                             authorization: str | None = Header(default=None, alias="Authorization"),
                             uc=Depends(get_actualizar_espacio_uc)):
    token = extract_bearer_token(authorization)
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="Nada para actualizar")
    return await uc.execute(token, espacio_id, data)

# Endpoint DELETE para eliminar un espacio.
# Extrae token y ejecuta el caso de uso con el ID del espacio.
@router.delete("/{espacio_id}")
async def eliminar_espacio(espacio_id: str,
                           authorization: str | None = Header(default=None, alias="Authorization"),
                           uc=Depends(get_eliminar_espacio_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id)

# Endpoint POST para ingestar texto en un espacio.
# Extrae token y ejecuta el caso de uso con título, texto y parámetros de chunking.
@router.post("/{espacio_id}/texto")
async def ingestar_texto(espacio_id: str, req: IngestarTextoRequest,
                         authorization: str | None = Header(default=None, alias="Authorization"),
                         uc=Depends(get_ingestar_texto_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id, req.titulo, req.texto, req.tam_chunk, req.overlap)
