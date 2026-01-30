from app.infrastructure.config.settings import settings
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient
from app.infrastructure.persistence.supabase.espacios_repo import EspaciosRepo

from app.application.use_cases.crear_espacio import CrearEspacioUseCase
from app.application.use_cases.listar_espacios import ListarEspaciosUseCase
from app.application.use_cases.obtener_espacio import ObtenerEspacioUseCase
from app.application.use_cases.actualizar_espacio import ActualizarEspacioUseCase
from app.application.use_cases.eliminar_espacio import EliminarEspacioUseCase

def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_espacios_repo():
    return EspaciosRepo(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_crear_espacio_uc():
    return CrearEspacioUseCase(get_auth_client(), get_espacios_repo())

def get_listar_espacios_uc():
    return ListarEspaciosUseCase(get_espacios_repo())

def get_obtener_espacio_uc():
    return ObtenerEspacioUseCase(get_espacios_repo())

def get_actualizar_espacio_uc():
    return ActualizarEspacioUseCase(get_espacios_repo())

def get_eliminar_espacio_uc():
    return EliminarEspacioUseCase(get_espacios_repo())



from app.infrastructure.ai.embeddings_model import EmbeddingsModel
from app.infrastructure.persistence.supabase.textos_espacio_repo import TextosEspacioRepo
from app.infrastructure.persistence.supabase.embeddings_repo import EmbeddingsRepo
from app.application.use_cases.ingestar_texto_espacio import IngestarTextoEspacioUseCase

_embeddings_model = EmbeddingsModel()

def get_textos_repo():
    return TextosEspacioRepo(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_embeddings_repo():
    return EmbeddingsRepo(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_ingestar_texto_uc():
    return IngestarTextoEspacioUseCase(
        get_auth_client(),
        get_espacios_repo(),
        get_textos_repo(),
        get_embeddings_repo(),
        _embeddings_model
    )

