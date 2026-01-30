# app/interfaces/api/dependencies/chat_deps.py
from app.infrastructure.config.settings import settings
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient
from app.infrastructure.persistence.supabase.chat_repository_postgrest import ChatRepositoryPostgrest
from app.infrastructure.persistence.supabase.recomendacion_repository_postgrest import RecomendacionRepositoryPostgrest
from app.infrastructure.ai.embeddings_model import EmbeddingsModel
from app.infrastructure.persistence.supabase.busqueda_semantica_rpc import BusquedaSemanticaRPC

from app.application.use_cases.create_chat import CreateChatUseCase
from app.application.use_cases.list_chats import ListChatsUseCase
from app.application.use_cases.get_chat_history import GetChatHistoryUseCase
from app.application.use_cases.send_message import SendMessageUseCase
from app.application.use_cases.enviar_mensaje_con_recomendaciones import EnviarMensajeConRecomendacionesUseCase
from app.application.services.orquestador_recomendaciones import OrquestadorRecomendaciones

from app.infrastructure.llm.gemini_client import GeminiClient


# singletons livianos
_embeddings_model = EmbeddingsModel()
_llm_client = GeminiClient()


def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_chat_repo():
    return ChatRepositoryPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_recomendacion_repo():
    return RecomendacionRepositoryPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_busqueda_rpc():
    return BusquedaSemanticaRPC(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_orquestador_recomendaciones():
    return OrquestadorRecomendaciones(_embeddings_model, get_busqueda_rpc(), get_recomendacion_repo())

def get_llm_client():
    return _llm_client


def get_create_chat_uc():
    return CreateChatUseCase(get_auth_client(), get_chat_repo())

def get_list_chats_uc():
    return ListChatsUseCase(get_chat_repo())

def get_get_history_uc():
    return GetChatHistoryUseCase(get_chat_repo())

def get_send_message_uc():
    return SendMessageUseCase(get_auth_client(), get_chat_repo())

def get_enviar_mensaje_con_recomendaciones_uc():
    return EnviarMensajeConRecomendacionesUseCase(
        get_auth_client(),
        get_chat_repo(),
        get_recomendacion_repo(),
        get_orquestador_recomendaciones(),
        get_llm_client(),
    )
