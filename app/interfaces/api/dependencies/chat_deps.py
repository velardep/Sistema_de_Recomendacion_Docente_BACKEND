# app/interfaces/api/dependencies/chat_deps.py

# Este archivo gestiona las dependencias para el sistema de chat.
# Proporciona funciones para instanciar repositorios de chat, recomendaciones,
# modelos de IA, clasificadores y casos de uso para crear chats, enviar mensajes
# y manejar recomendaciones. Utiliza singletons para componentes pesados.
# Facilita la inyección de dependencias en las rutas de chat de la API.

# Configuración del sistema
from app.infrastructure.config.settings import settings

# Infraestructura - Seguridad
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient

# Infraestructura - Persistencia
from app.infrastructure.persistence.supabase.chat_repository_postgrest import ChatRepositoryPostgrest
from app.infrastructure.persistence.supabase.recomendacion_repository_postgrest import RecomendacionRepositoryPostgrest
from app.infrastructure.persistence.supabase.busqueda_semantica_rpc import BusquedaSemanticaRPC
from app.infrastructure.persistence.supabase.red3_repo import Red3RepoPostgrest

# Infraestructura - Modelos de IA
from app.infrastructure.ai.embeddings_model import EmbeddingsModel
from app.infrastructure.llm.gemini_client import GeminiClient
from app.infrastructure.ai.red3_classifier import Red3Classifier

# Aplicación - Casos de uso
from app.application.use_cases.create_chat import CreateChatUseCase
from app.application.use_cases.list_chats import ListChatsUseCase
from app.application.use_cases.get_chat_history import GetChatHistoryUseCase
from app.application.use_cases.send_message import SendMessageUseCase
from app.application.use_cases.enviar_mensaje_con_recomendaciones import EnviarMensajeConRecomendacionesUseCase

# Aplicación - Servicios
from app.application.services.orquestador_recomendaciones import OrquestadorRecomendaciones
from app.application.services.red3_service import Red3Service

# Dependencias externas de otros módulos de dependencias
from app.interfaces.api.dependencies.red3_deps import get_red3_service


# Crea instancias singleton de modelos y servicios livianos para reutilización
_embeddings_model = EmbeddingsModel()
_llm_client = GeminiClient()

_red3_classifier = Red3Classifier(settings.RED3_EXPORT_DIR)
_red3_repo = Red3RepoPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
_red3_service = Red3Service(_red3_repo, _red3_classifier)

# Crea y devuelve una instancia del cliente de autenticación de Supabase
def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del repositorio de chats
def get_chat_repo():
    return ChatRepositoryPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del repositorio de recomendaciones
def get_recomendacion_repo():
    return RecomendacionRepositoryPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del RPC para búsquedas semánticas
def get_busqueda_rpc():
    return BusquedaSemanticaRPC(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del orquestador de recomendaciones
def get_orquestador_recomendaciones():
    return OrquestadorRecomendaciones(_embeddings_model, get_busqueda_rpc(), get_recomendacion_repo())

# Crea y devuelve una instancia del cliente LLM
def get_llm_client():
    return _llm_client

# Crea y devuelve el caso de uso para crear un nuevo chat
def get_create_chat_uc():
    return CreateChatUseCase(get_auth_client(), get_chat_repo())

# Crea y devuelve el caso de uso para listar chats
def get_list_chats_uc():
    return ListChatsUseCase(get_chat_repo())

# Crea y devuelve el caso de uso para obtener el historial de un chat
def get_get_history_uc():
    return GetChatHistoryUseCase(get_chat_repo())

# Crea y devuelve el caso de uso para enviar un mensaje simple
def get_send_message_uc():
    return SendMessageUseCase(get_auth_client(), get_chat_repo())

# Crea y devuelve el caso de uso para enviar mensaje con recomendaciones
def get_enviar_mensaje_con_recomendaciones_uc():
    return EnviarMensajeConRecomendacionesUseCase(
        get_auth_client(),
        get_chat_repo(),
        get_orquestador_recomendaciones(),
        get_llm_client(),
        red3_service=get_red3_service(),  

    )
