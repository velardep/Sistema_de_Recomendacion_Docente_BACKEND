from fastapi import APIRouter, Depends, HTTPException, Header
from app.interfaces.api.schemas.me import UpsertMeRequest
from app.interfaces.api.dependencies.auth_deps import get_get_me_uc, get_upsert_me_uc
from app.application.use_cases.get_me import GetMeUseCase
from app.application.use_cases.upsert_me import UpsertMeUseCase

router = APIRouter(prefix="/me", tags=["me"])

def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Use: Bearer <token>")
    return authorization.split(" ", 1)[1].strip()

@router.get("")
async def me(
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: GetMeUseCase = Depends(get_get_me_uc),
):
    try:
        token = extract_bearer_token(authorization)
        return await uc.execute(token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("")
async def upsert_me(
    req: UpsertMeRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: UpsertMeUseCase = Depends(get_upsert_me_uc),
):
    try:
        token = extract_bearer_token(authorization)
        return await uc.execute(token, req.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
