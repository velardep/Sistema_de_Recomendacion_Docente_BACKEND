from fastapi import APIRouter, Depends, Header, HTTPException
from app.interfaces.api.schemas.espacios import CrearEspacioRequest, ActualizarEspacioRequest
from app.interfaces.api.routes.busqueda import extract_bearer_token  # ya lo tienes
from app.interfaces.api.dependencies.espacios_deps import (
    get_crear_espacio_uc, get_listar_espacios_uc, get_obtener_espacio_uc,
    get_actualizar_espacio_uc, get_eliminar_espacio_uc
)

router = APIRouter(prefix="/espacios", tags=["espacios"])

@router.post("")
async def crear_espacio(req: CrearEspacioRequest,
                       authorization: str | None = Header(default=None, alias="Authorization"),
                       uc=Depends(get_crear_espacio_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, req.model_dump(exclude_none=True))

@router.get("")
async def listar_espacios(authorization: str | None = Header(default=None, alias="Authorization"),
                          uc=Depends(get_listar_espacios_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token)

@router.get("/{espacio_id}")
async def obtener_espacio(espacio_id: str,
                          authorization: str | None = Header(default=None, alias="Authorization"),
                          uc=Depends(get_obtener_espacio_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id)

@router.patch("/{espacio_id}")
async def actualizar_espacio(espacio_id: str, req: ActualizarEspacioRequest,
                             authorization: str | None = Header(default=None, alias="Authorization"),
                             uc=Depends(get_actualizar_espacio_uc)):
    token = extract_bearer_token(authorization)
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="Nada para actualizar")
    return await uc.execute(token, espacio_id, data)

@router.delete("/{espacio_id}")
async def eliminar_espacio(espacio_id: str,
                           authorization: str | None = Header(default=None, alias="Authorization"),
                           uc=Depends(get_eliminar_espacio_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id)



from app.interfaces.api.schemas.ingesta_texto import IngestarTextoRequest
from app.interfaces.api.dependencies.espacios_deps import get_ingestar_texto_uc

@router.post("/{espacio_id}/texto")
async def ingestar_texto(espacio_id: str, req: IngestarTextoRequest,
                         authorization: str | None = Header(default=None, alias="Authorization"),
                         uc=Depends(get_ingestar_texto_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id, req.titulo, req.texto, req.tam_chunk, req.overlap)
