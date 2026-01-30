from app.infrastructure.config.settings import settings
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient
from app.infrastructure.persistence.supabase.docente_repository_postgrest import DocenteRepositoryPostgrest

from app.application.use_cases.auth_register import AuthRegisterUseCase
from app.application.use_cases.auth_login import AuthLoginUseCase
from app.application.use_cases.get_me import GetMeUseCase
from app.application.use_cases.upsert_me import UpsertMeUseCase

def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_docente_repo():
    return DocenteRepositoryPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_register_uc():
    return AuthRegisterUseCase(get_auth_client())

def get_login_uc():
    return AuthLoginUseCase(get_auth_client())

def get_get_me_uc():
    return GetMeUseCase(get_auth_client(), get_docente_repo())

def get_upsert_me_uc():
    return UpsertMeUseCase(get_auth_client(), get_docente_repo())
