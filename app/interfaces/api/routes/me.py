# app/interfaces/api/routes/me.py

# Este archivo define las rutas de la API para gestión del perfil de usuario (/me).
# Incluye endpoints para obtener y actualizar la información del usuario autenticado,
# utilizando casos de uso para manejar la lógica de negocio.
# Gestiona autenticación vía tokens Bearer y validaciones de datos.

# Framework - FastAPI
from fastapi import APIRouter, Depends, HTTPException, Header

# Interfaces - Esquemas de API
from app.interfaces.api.schemas.me import UpsertMeRequest

# Interfaces - Dependencias
from app.interfaces.api.dependencies.auth_deps import get_get_me_uc, get_upsert_me_uc

# Aplicación - Casos de uso
from app.application.use_cases.get_me import GetMeUseCase
from app.application.use_cases.upsert_me import UpsertMeUseCase

# Creación del router para rutas de perfil de usuario con prefijo /me y etiqueta me.
router = APIRouter(prefix="/me", tags=["me"])

# Función utilitaria para extraer el token Bearer del header de autorización.
# Valida que el header exista y comience con "Bearer", luego extrae el token.
def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Use: Bearer <token>")
    return authorization.split(" ", 1)[1].strip()

# Endpoint GET para obtener la información del perfil del usuario.
# Extrae token y ejecuta el caso de uso; validación adicional se maneja globalmente.
@router.get("")
async def me(
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: GetMeUseCase = Depends(get_get_me_uc),
):
    # solo validamos bearer aquí; lo demás lo maneja el handler global
    token = extract_bearer_token(authorization)
    return await uc.execute(token)

# Endpoint POST para actualizar o insertar la información del perfil del usuario.
# Extrae token y ejecuta el caso de uso con los datos del perfil.
@router.post("")
async def upsert_me(
    req: UpsertMeRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: UpsertMeUseCase = Depends(get_upsert_me_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, req.model_dump())