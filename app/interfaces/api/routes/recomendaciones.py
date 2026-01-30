from fastapi import APIRouter, Depends, HTTPException, Header
from app.interfaces.api.schemas.recomendaciones import CrearRecomendacionRequest, RegistrarAccionRequest
from app.interfaces.api.dependencies.recomendaciones_deps import (
    get_crear_recomendacion_uc, get_listar_recomendaciones_uc,
    get_registrar_accion_uc, get_listar_acciones_uc
)
from app.application.use_cases.crear_recomendacion import CrearRecomendacionUseCase
from app.application.use_cases.listar_recomendaciones import ListarRecomendacionesUseCase
from app.application.use_cases.registrar_accion_docente import RegistrarAccionDocenteUseCase
from app.application.use_cases.listar_acciones_recomendacion import ListarAccionesRecomendacionUseCase

router = APIRouter(prefix="/recomendaciones", tags=["recomendaciones"])

def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Use: Bearer <token>")
    return authorization.split(" ", 1)[1].strip()

@router.post("")
async def crear_recomendacion(
    req: CrearRecomendacionRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: CrearRecomendacionUseCase = Depends(get_crear_recomendacion_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, req.model_dump())

@router.get("")
async def listar_recomendaciones(
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: ListarRecomendacionesUseCase = Depends(get_listar_recomendaciones_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token)

@router.post("/{recomendacion_id}/acciones")
async def registrar_accion(
    recomendacion_id: str,
    req: RegistrarAccionRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: RegistrarAccionDocenteUseCase = Depends(get_registrar_accion_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, recomendacion_id, req.model_dump())

@router.get("/{recomendacion_id}/acciones")
async def listar_acciones(
    recomendacion_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: ListarAccionesRecomendacionUseCase = Depends(get_listar_acciones_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, recomendacion_id)
