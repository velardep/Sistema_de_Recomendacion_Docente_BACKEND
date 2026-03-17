# app/interfaces/api/dependencies/busqueda_deps.py

# Este archivo gestiona las dependencias para la búsqueda semántica.
# Proporciona funciones para crear instancias de modelos de embeddings,
# clientes de autenticación, RPC para búsquedas y el caso de uso de búsqueda.
# Utiliza singletons para el modelo de embeddings para eficiencia.
# Facilita la inyección de dependencias en las rutas de búsqueda de la API.

# Configuración del sistema
from app.infrastructure.config.settings import settings

# Componentes de infraestructura: seguridad, modelos de IA y persistencia
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient
from app.infrastructure.ai.embeddings_model import EmbeddingsModel
from app.infrastructure.persistence.supabase.busqueda_semantica_rpc import BusquedaSemanticaRPC

# Casos de uso de la aplicación para búsqueda semántica
from app.application.use_cases.buscar_semantico import BuscarSemanticoUseCase

# Crea un singleton del modelo de embeddings para reutilización
# Instancia global del modelo de embeddings
_embeddings_model = EmbeddingsModel()

# Crea y devuelve una instancia del cliente de autenticación de Supabase
def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del RPC para búsquedas semánticas
def get_rpc():
    return BusquedaSemanticaRPC(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve el caso de uso para realizar búsquedas semánticas
def get_busqueda_uc():
    return BuscarSemanticoUseCase(get_auth_client(), _embeddings_model, get_rpc())
