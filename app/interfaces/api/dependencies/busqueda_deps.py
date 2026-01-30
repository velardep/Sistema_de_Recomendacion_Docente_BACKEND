from app.infrastructure.config.settings import settings
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient
from app.infrastructure.ai.embeddings_model import EmbeddingsModel
from app.infrastructure.persistence.supabase.busqueda_semantica_rpc import BusquedaSemanticaRPC
from app.application.use_cases.buscar_semantico import BuscarSemanticoUseCase

# singletons simples
_embeddings_model = EmbeddingsModel()

def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_rpc():
    return BusquedaSemanticaRPC(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_busqueda_uc():
    return BuscarSemanticoUseCase(get_auth_client(), _embeddings_model, get_rpc())
