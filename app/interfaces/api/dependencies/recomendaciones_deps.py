from app.infrastructure.config.settings import settings
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient
from app.infrastructure.persistence.supabase.recomendacion_repository_postgrest import RecomendacionRepositoryPostgrest

from app.application.use_cases.crear_recomendacion import CrearRecomendacionUseCase
from app.application.use_cases.listar_recomendaciones import ListarRecomendacionesUseCase
from app.application.use_cases.registrar_accion_docente import RegistrarAccionDocenteUseCase
from app.application.use_cases.listar_acciones_recomendacion import ListarAccionesRecomendacionUseCase

def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_repo():
    return RecomendacionRepositoryPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_crear_recomendacion_uc():
    return CrearRecomendacionUseCase(get_auth_client(), get_repo())

def get_listar_recomendaciones_uc():
    return ListarRecomendacionesUseCase(get_repo())

def get_registrar_accion_uc():
    return RegistrarAccionDocenteUseCase(get_auth_client(), get_repo())

def get_listar_acciones_uc():
    return ListarAccionesRecomendacionUseCase(get_repo())
