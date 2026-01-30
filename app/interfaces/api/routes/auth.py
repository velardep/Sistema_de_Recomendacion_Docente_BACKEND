from fastapi import APIRouter, Depends, HTTPException
import httpx

from app.interfaces.api.schemas.auth import RegisterRequest, LoginRequest
from app.interfaces.api.dependencies.auth_deps import get_register_uc, get_login_uc
from app.application.use_cases.auth_register import AuthRegisterUseCase
from app.application.use_cases.auth_login import AuthLoginUseCase

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(req: RegisterRequest, uc: AuthRegisterUseCase = Depends(get_register_uc)):
    try:
        return await uc.execute(req.email, req.password)
    except httpx.HTTPStatusError as e:
        # Devuelve el error real de Supabase
        try:
            detail = e.response.json()
        except Exception:
            detail = e.response.text
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(req: LoginRequest, uc: AuthLoginUseCase = Depends(get_login_uc)):
    try:
        return await uc.execute(req.email, req.password)
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json()
        except Exception:
            detail = e.response.text
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
