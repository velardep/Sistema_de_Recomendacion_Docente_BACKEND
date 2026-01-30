from fastapi import APIRouter, Depends, Header
from app.interfaces.api.schemas.busqueda_mixta import BusquedaMixtaRequest
from app.interfaces.api.dependencies.busqueda_mixta_deps import get_busqueda_mixta_uc
from app.interfaces.api.routes.busqueda import extract_bearer_token  # ya lo tienes

router = APIRouter(prefix="/espacios", tags=["busqueda-mixta"])

@router.post("/{espacio_id}/busqueda-mixta")
async def busqueda_mixta(espacio_id: str, req: BusquedaMixtaRequest,
                         authorization: str | None = Header(default=None, alias="Authorization"),
                         uc=Depends(get_busqueda_mixta_uc)):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id, req.model_dump())
