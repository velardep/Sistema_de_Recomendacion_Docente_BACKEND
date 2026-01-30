# app/interfaces/api/dependencies/espacio_deps.py

from app.infrastructure.config.settings import settings
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient

# AI / LLM
from app.infrastructure.ai.embeddings_model import EmbeddingsModel
from app.infrastructure.llm.gemini_client import GeminiClient

# Persistence
from app.infrastructure.persistence.supabase.busqueda_semantica_rpc import BusquedaSemanticaRPC
from app.infrastructure.persistence.supabase.espacios_repo import EspaciosRepo
from app.infrastructure.persistence.supabase.chat_espacios_repo import ChatEspaciosRepo
from app.infrastructure.persistence.supabase.recomendaciones_espacio_repo import RecomendacionesEspacioRepo
from app.infrastructure.persistence.supabase.embeddings_repo import EmbeddingsRepo

# Application
from app.application.services.orquestador_rag_espacio import OrquestadorRAGEspacio
from app.application.use_cases.busqueda_mixta_espacio import BusquedaMixtaEspacioUseCase
from app.application.use_cases.crear_chat_espacio import CrearChatEspacioUseCase
from app.application.use_cases.enviar_mensaje_espacio_plus import EnviarMensajeEspacioPlusUseCase
from app.application.use_cases.ingestar_archivo_espacio import IngestarArchivoEspacioUseCase


from app.application.use_cases.listar_chats_espacio import ListarChatsEspacioUseCase
from app.application.use_cases.obtener_chat_espacio import ObtenerChatEspacioUseCase

# =====================================================
# Singletons (componentes pesados)
# =====================================================
_embeddings_model = EmbeddingsModel()
_llm_client = GeminiClient()


# =====================================================
# Clients
# =====================================================
def get_auth_client():
    return SupabaseAuthClient(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )

def get_busqueda_rpc():
    return BusquedaSemanticaRPC(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )

def get_llm_client():
    return _llm_client


# =====================================================
# Repositories
# =====================================================
def get_espacios_repo():
    return EspaciosRepo(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )

def get_chat_espacios_repo():
    return ChatEspaciosRepo(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )

def get_recomendaciones_espacio_repo():
    return RecomendacionesEspacioRepo(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )

def get_embeddings_repo():
    return EmbeddingsRepo(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )


# =====================================================
# Use Cases
# =====================================================
def get_crear_chat_espacio_uc():
    return CrearChatEspacioUseCase(
        get_auth_client(),
        get_espacios_repo(),
        get_chat_espacios_repo(),
    )

def get_busqueda_mixta_uc():
    return BusquedaMixtaEspacioUseCase(
        get_auth_client(),
        _embeddings_model,
        get_busqueda_rpc(),
        get_espacios_repo(),
    )


def get_orquestador_rag_espacio():
    return OrquestadorRAGEspacio(
        _embeddings_model,
        get_busqueda_rpc(),
    )

def get_enviar_mensaje_espacio_plus_uc():
    return EnviarMensajeEspacioPlusUseCase(
        get_auth_client(),
        get_espacios_repo(),
        get_chat_espacios_repo(),
        get_recomendaciones_espacio_repo(),
        get_orquestador_rag_espacio(),
        get_llm_client(),
    )

def get_ingestar_archivo_espacio_uc():
    return IngestarArchivoEspacioUseCase(
        get_auth_client(),
        get_espacios_repo(),
        _embeddings_model,
        get_embeddings_repo(),
    )



# agrega al final de app/interfaces/api/dependencies/chat_espacio_deps.py



# =====================================================
# Use Cases EXTRA (GET list chats + GET historial chat)
# =====================================================

def get_listar_chats_espacio_uc():
    # Lista conversaciones del espacio (validando espacio por RLS)
    return ListarChatsEspacioUseCase(
        get_espacios_repo(),
        get_chat_espacios_repo(),
    )

def get_historial_chat_espacio_uc():
    # Obtiene conversación + mensajes (validando espacio por RLS)
    return ObtenerChatEspacioUseCase(
        get_espacios_repo(),
        get_chat_espacios_repo(),
    )

# ✅ ALIAS para que coincida con lo que tu router importará (si usas estos nombres)
def get_get_chat_espacio_history_uc():
    return get_historial_chat_espacio_uc()
