# app/interfaces/api/routes/auth.py

# Este archivo define las rutas de la API para autenticación de usuarios.
# Incluye endpoints para registro y login, utilizando casos de uso para manejar la lógica.
# Gestiona errores de Supabase y excepciones generales, devolviendo respuestas HTTP apropiadas.
# Forma parte del sistema de autenticación basado en Supabase.

# Librerías estándar
import httpx

# Framework - FastAPI
from fastapi import APIRouter, Depends, HTTPException

# Interfaces - Esquemas de API
from app.interfaces.api.schemas.auth import RegisterRequest, LoginRequest

# Interfaces - Dependencias
from app.interfaces.api.dependencies.auth_deps import get_register_uc, get_login_uc

# Aplicación - Casos de uso
from app.application.use_cases.auth_register import AuthRegisterUseCase
from app.application.use_cases.auth_login import AuthLoginUseCase

# Creación del router para rutas de autenticación con prefijo /auth y etiqueta auth.
router = APIRouter(prefix="/auth", tags=["auth"])

# Endpoint POST para registro de usuarios.
# Recibe datos de registro, ejecuta el caso de uso y maneja errores.
@router.post("/register")
async def register(req: RegisterRequest, uc: AuthRegisterUseCase = Depends(get_register_uc)):
    try:
        # Ejecuta el caso de uso de registro con email y contraseña.
        return await uc.execute(req.email, req.password)
    except httpx.HTTPStatusError as e:
        # Maneja errores HTTP de Supabase, intentando extraer detalles JSON.
        # Si falla, usa el texto de la respuesta.
        try:
            detail = e.response.json()
        except Exception:
            detail = e.response.text
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except Exception as e:
        # Maneja otras excepciones con código 400 y mensaje de error.
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint POST para login de usuarios.
# Recibe credenciales, ejecuta el caso de uso y maneja errores similares al registro.
@router.post("/login")
async def login(req: LoginRequest, uc: AuthLoginUseCase = Depends(get_login_uc)):
    try:
        # Ejecuta el caso de uso de login con email y contraseña.
        return await uc.execute(req.email, req.password)
    except httpx.HTTPStatusError as e:
        # Maneja errores HTTP de Supabase, intentando extraer detalles JSON.
        # Si falla, usa el texto de la respuesta.
        try:
            detail = e.response.json()
        except Exception:
            detail = e.response.text
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except Exception as e:
        # Maneja otras excepciones con código 400 y mensaje de error.
        raise HTTPException(status_code=400, detail=str(e))
