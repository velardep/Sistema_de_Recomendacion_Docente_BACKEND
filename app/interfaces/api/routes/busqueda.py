from fastapi import APIRouter, Depends, Header, HTTPException
from app.interfaces.api.schemas.busqueda import BusquedaSemanticaRequest
from app.interfaces.api.dependencies.busqueda_deps import get_busqueda_uc
from app.application.use_cases.buscar_semantico import BuscarSemanticoUseCase

router = APIRouter(prefix="/busqueda", tags=["busqueda"])

def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Use: Bearer <token>")
    return authorization.split(" ", 1)[1].strip()

@router.post("/semantica")
async def busqueda_semantica(
    req: BusquedaSemanticaRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: BuscarSemanticoUseCase = Depends(get_busqueda_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, req.texto, req.top_k, req.tipo_fuente, req.espacio_id)
