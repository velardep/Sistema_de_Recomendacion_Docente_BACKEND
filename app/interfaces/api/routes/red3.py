# app/interfaces/api/routes/red3.py

# Este archivo define las rutas de la API para operaciones con RED3.
# Incluye endpoints para obtener perfiles, snapshots, ejecutar análisis manual
# y generar recomendaciones con LLM, integrando autenticación y caching.
# Gestiona datos de estilo docente y recomendaciones pedagógicas.

# Framework - FastAPI
from fastapi import APIRouter, Depends, Header

# Librerías
from pydantic import BaseModel

# Librerías estándar
from datetime import datetime, date, timezone

# Interfaces - Utilidades de rutas
from app.interfaces.api.routes.busqueda import extract_bearer_token

# Interfaces - Dependencias
from app.interfaces.api.dependencies.red3_deps import (
    get_auth_client, 
    get_red3_service,
    get_llm_client,
    get_red3_llm_recs_repo)

# Aplicación - Casos de uso
from app.application.use_cases.obtener_perfil_red3 import ObtenerPerfilRed3UseCase
from app.application.use_cases.generar_recomendaciones_red3 import GenerarRecomendacionesRed3UseCase


# Creación del router para rutas de RED3 con prefijo /red3 y etiqueta red3.
router = APIRouter(prefix="/red3", tags=["red3"])

# Modelo Pydantic para solicitud de ejecución manual de RED3.
class RunNowRequest(BaseModel):
    window_days: int = 30
    period_end: str | None = None  # 'YYYY-MM-DD'

# Modelo Pydantic para consulta de recomendaciones.
class RecsQuery(BaseModel):
    window_days: int = 30
    force: bool = False # fuerza regeneración ignorando cache

# Función que crea y retorna el caso de uso para obtener perfil RED3.
def get_perfil_uc(
    auth=Depends(get_auth_client),
    red3=Depends(get_red3_service),
):
    return ObtenerPerfilRed3UseCase(auth, red3)

# Función que crea y retorna el caso de uso para generar recomendaciones RED3.
def get_recs_uc(
    auth=Depends(get_auth_client),
    red3=Depends(get_red3_service),
    llm=Depends(get_llm_client),
    cache_repo=Depends(get_red3_llm_recs_repo),
):
    return GenerarRecomendacionesRed3UseCase(auth, red3, llm, cache_repo)

# Función utilitaria para parsear fechas que pueden venir en diferentes formatos.
# Maneja datetime, strings ISO y formatos con espacio, retornando datetime o None.
def _parse_dt_maybe(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip()
    # intenta ISO primero
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        pass
    # intenta formato con espacio
    try:
        # ejemplo: '2026-02-22 22:40:39.241428+00'
        return datetime.fromisoformat(s.replace(" ", "T"))
    except Exception:
        return None

# Endpoint GET para obtener el perfil RED3 del usuario.
# Extrae token y ejecuta el caso de uso para retornar el perfil.
@router.get("/perfil")
async def get_perfil(
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: ObtenerPerfilRed3UseCase = Depends(get_perfil_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token)

# Endpoint GET para obtener el estilo personal del usuario con snapshots y meta de recomendaciones.
# Obtiene perfil, snapshots de 7d y 30d, calcula si toca refrescar recomendaciones.
@router.get("/me")
async def get_my_style(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth=Depends(get_auth_client),
    red3=Depends(get_red3_service),
):
    # Extrae el token Bearer del header de autorización para autenticar la solicitud.
    token = extract_bearer_token(authorization)
    user = await auth.get_user(token)
    docente_id = user["id"]

    # Consulta el repositorio para obtener el perfil de estilo docente actual si existe.
    prof = await red3.repo.get_style_profile(token, docente_id)

    # Recupera el snapshot más reciente de los últimos 7 y 3o días si están disponible.
    snap7 = await red3.repo.get_latest_snapshot(token, docente_id, window_days=7)
    snap30 = await red3.repo.get_latest_snapshot(token, docente_id, window_days=30)

    # Obtiene la marca de tiempo actual en zona horaria UTC para cálculos temporales.
    now = datetime.now(timezone.utc)

    # Selecciona el snapshot de referencia, priorizando 30 días sobre 7 días.
    # Parsea la fecha de creación del snapshot de referencia usando la función utilitaria.
    snap_ref = snap30 or snap7 or {}
    snap_created_at = _parse_dt_maybe(snap_ref.get("created_at")) if isinstance(snap_ref, dict) else None

    # Define el período de refresco para recomendaciones en días.
    refresh_days = 3
    # Inicializa el indicador de vencimiento como verdadero por defecto.
    due = True
    # Si existe una fecha de creación, calcula si han transcurrido los días de refresco.
    if snap_created_at:
        delta_days = (now - snap_created_at).total_seconds() / 86400.0
        due = delta_days >= float(refresh_days)

    # Construye el objeto meta con información para determinar si se deben refrescar las recomendaciones.
    reco_meta = {
        "refresh_days": refresh_days,
        "server_now": now.isoformat(),
        "snapshot_ref_created_at": snap_created_at.isoformat() if snap_created_at else None,
        "due": due,
    }

    # Retorna la respuesta JSON con perfil, snapshots, meta de recomendaciones y placeholder para LLM.
    return {
        "profile": prof,
        "snapshot_7d": snap7,
        "snapshot_30d": snap30,
        "reco_meta": reco_meta,
        "llm_recommendations": None,
    }

# Endpoint POST para ejecutar análisis RED3 manualmente.
# Actualiza perfil, obtiene datos actualizados y calcula meta de recomendaciones.
@router.post("/run-now")
async def run_red3_now(
    req: RunNowRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth=Depends(get_auth_client),
    red3=Depends(get_red3_service),
):
    # Extrae el token Bearer del header para validar la autenticación del usuario.
    token = extract_bearer_token(authorization)
    user = await auth.get_user(token)
    docente_id = user["id"]

    # Determina la fecha de fin del período, usando la proporcionada o la fecha actual.
    period_end = req.period_end or datetime.now(timezone.utc).date().isoformat()

    # Ejecuta la actualización del perfil de manera best-effort con los parámetros especificados.
    await red3.update_profile_best_effort(
        token,
        docente_id=docente_id,
        period_end=period_end,
        window_days=int(req.window_days),
    )

    # Consulta el perfil de estilo actualizado después de la ejecución.
    prof = await red3.repo.get_style_profile(token, docente_id)
    
    # Obtiene el snapshot más reciente de 7 y 30 días post-ejecución.
    snap7 = await red3.repo.get_latest_snapshot(token, docente_id, window_days=7)
    snap30 = await red3.repo.get_latest_snapshot(token, docente_id, window_days=30)

    # Calcula el meta de recomendaciones de la misma manera que en /me.
    now = datetime.now(timezone.utc)
    snap_ref = snap30 or snap7 or {}
    snap_created_at = _parse_dt_maybe(snap_ref.get("created_at")) if isinstance(snap_ref, dict) else None

    refresh_days = 3
    due = True
    if snap_created_at:
        delta_days = (now - snap_created_at).total_seconds() / 86400.0
        due = delta_days >= float(refresh_days)

    reco_meta = {
        "refresh_days": refresh_days,
        "server_now": now.isoformat(),
        "snapshot_ref_created_at": snap_created_at.isoformat() if snap_created_at else None,
        "due": due,
    }

    # Retorna una respuesta de confirmación con todos los datos actualizados.
    return {
        "ok": True,
        "profile": prof,
        "snapshot_7d": snap7,
        "snapshot_30d": snap30,
        "reco_meta": reco_meta,
        "llm_recommendations": None,
    }

# Endpoint POST para obtener recomendaciones LLM con caching de 3 días.
# Ejecuta el caso de uso con parámetros de ventana y fuerza de regeneración.
@router.post("/recomendaciones")
async def red3_recomendaciones(
    req: RecsQuery,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: GenerarRecomendacionesRed3UseCase = Depends(get_recs_uc),
):
    # Extrae el token Bearer del header para autenticar la solicitud de recomendaciones.
    token = extract_bearer_token(authorization)
    # Ejecuta el caso de uso de generación de recomendaciones con los parámetros especificados.
    return await uc.execute(
        token,
        window_days=int(req.window_days),
        force=bool(req.force),
    )