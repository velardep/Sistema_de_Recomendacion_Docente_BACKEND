# app/interfaces/api/dependencies/auth_deps.py

# Este archivo contiene las dependencias de inyección
# para los casos de uso relacionados con la autenticación y gestión de usuarios.
# Proporciona funciones que crean instancias de clientes de autenticación,
# repositorios de docentes y casos de uso para registro, login y perfil de usuario.
# Facilita la inyección de dependencias en las rutas de la API.

# Configuración del sistema
from app.infrastructure.config.settings import settings

# Componentes de infraestructura: seguridad y persistencia
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient
from app.infrastructure.persistence.supabase.docente_repository_postgrest import DocenteRepositoryPostgrest

# Casos de uso de la aplicación para autenticación y gestión de usuarios
from app.application.use_cases.auth_register import AuthRegisterUseCase
from app.application.use_cases.auth_login import AuthLoginUseCase
from app.application.use_cases.get_me import GetMeUseCase
from app.application.use_cases.upsert_me import UpsertMeUseCase

# Crea y devuelve una instancia del cliente de autenticación de Supabase
def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del repositorio de docentes
def get_docente_repo():
    return DocenteRepositoryPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve el caso de uso para registrar un nuevo usuario
def get_register_uc():
    return AuthRegisterUseCase(get_auth_client())

# Crea y devuelve el caso de uso para iniciar sesión
def get_login_uc():
    return AuthLoginUseCase(get_auth_client())

# Crea y devuelve el caso de uso para obtener el perfil del usuario actual
def get_get_me_uc():
    return GetMeUseCase(get_auth_client(), get_docente_repo())

# Crea y devuelve el caso de uso para actualizar el perfil del usuario
def get_upsert_me_uc():
    return UpsertMeUseCase(get_auth_client(), get_docente_repo())
