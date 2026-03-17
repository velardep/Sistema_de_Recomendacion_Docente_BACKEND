# app/interfaces/api/dependencies/busqueda_mixta_deps.py

# Este archivo maneja las dependencias para la búsqueda mixta en espacios.
# Proporciona funciones para instanciar modelos de embeddings, clientes de autenticación,
# RPC de búsquedas, repositorios de espacios y el caso de uso de búsqueda mixta.
# Utiliza un singleton para el modelo de embeddings.
# Simplifica la inyección de dependencias en las rutas de búsqueda mixta.

# Configuración del sistema
from app.infrastructure.config.settings import settings

# Componentes de infraestructura: seguridad, modelos de IA y persistencia
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient
from app.infrastructure.ai.embeddings_model import EmbeddingsModel
from app.infrastructure.persistence.supabase.busqueda_semantica_rpc import BusquedaSemanticaRPC
from app.infrastructure.persistence.supabase.espacios_repo import EspaciosRepo

# Casos de uso de la aplicación para búsqueda mixta en espacios
from app.application.use_cases.busqueda_mixta_espacio import BusquedaMixtaEspacioUseCase

# Instancia singleton del modelo de embeddings
_embeddings_model = EmbeddingsModel()

# Crea y devuelve una instancia del cliente de autenticación de Supabase
def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del RPC para búsquedas semánticas
def get_busqueda_rpc():
    return BusquedaSemanticaRPC(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del repositorio de espacios
def get_espacios_repo():
    return EspaciosRepo(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve el caso de uso para búsqueda mixta en espacios
def get_busqueda_mixta_uc():
    return BusquedaMixtaEspacioUseCase(
        get_auth_client(),
        _embeddings_model,
        get_busqueda_rpc(),
        get_espacios_repo()
    )
