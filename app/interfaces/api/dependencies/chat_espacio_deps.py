# app/interfaces/api/dependencies/chat_espacio_deps.py

# Descripción del archivo: Este archivo centraliza todas las dependencias para el sistema de chat en espacios de trabajo.
# Gestiona la creación de singletons para modelos de IA, clasificadores de redes neuronales, repositorios de datos,
# servicios de orquestación y casos de uso para operaciones complejas como ingesta de archivos, búsquedas mixtas
# y envío de mensajes con recomendaciones. Utiliza un pool HTTP compartido para optimizar conexiones a Supabase.
# Es el núcleo de inyección de dependencias para las rutas de espacios de trabajo en la API.

# Librerías estándar y typing
from __future__ import annotations

import os
import httpx
import torch
from typing import Any, Callable

# Configuración del sistema
from app.infrastructure.config.settings import settings

# Infraestructura - Seguridad
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient

# Infraestructura - IA - Embeddings y LLM
from app.infrastructure.ai.embeddings_model import EmbeddingsModel
from app.infrastructure.llm.gemini_client import GeminiClient

# Infraestructura - IA - Clasificadores RED
from app.infrastructure.ai.red1_classifier import Red1Classifier
from app.infrastructure.ai.red2_classifier import Red2Classifier
from app.infrastructure.ai.red3_classifier import Red3Classifier

# Infraestructura - Persistencia - Repositorios generales
from app.infrastructure.persistence.supabase.busqueda_semantica_rpc import BusquedaSemanticaRPC
from app.infrastructure.persistence.supabase.espacios_repo import EspaciosRepo
from app.infrastructure.persistence.supabase.chat_espacios_repo import ChatEspaciosRepo
from app.infrastructure.persistence.supabase.embeddings_repo import EmbeddingsRepo

# Infraestructura - Persistencia - Repositorios RED
from app.infrastructure.persistence.supabase.red1_repo import Red1RepoPostgrest
from app.infrastructure.persistence.supabase.red2_repo import Red2Repo
from app.infrastructure.persistence.supabase.red3_repo import Red3RepoPostgrest

# Aplicación - Servicios
from app.application.services.red1_service import Red1Service
from app.application.services.red2_guidance import Red2GuidanceService
from app.application.services.red3_service import Red3Service
from app.application.services.orquestador_rag_espacio import OrquestadorRAGEspacio

# Aplicación - Casos de uso
from app.application.use_cases.busqueda_mixta_espacio import BusquedaMixtaEspacioUseCase
from app.application.use_cases.crear_chat_espacio import CrearChatEspacioUseCase
from app.application.use_cases.enviar_mensaje_espacio_plus import EnviarMensajeEspacioPlusUseCase
from app.application.use_cases.ingestar_archivo_espacio import IngestarArchivoEspacioUseCase
from app.application.use_cases.listar_chats_espacio import ListarChatsEspacioUseCase
from app.application.use_cases.obtener_chat_espacio import ObtenerChatEspacioUseCase

# Dependencias externas de otros módulos de dependencias
from app.interfaces.api.dependencies.red3_deps import get_red3_service

# Crea un cliente HTTP asíncrono compartido con configuración optimizada para conexiones persistentes
_supabase_http = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=10.0, read=60.0, write=20.0, pool=20.0),
    limits=httpx.Limits(
        max_connections=50,
        max_keepalive_connections=20,
        keepalive_expiry=60.0,
    ),
    http2=True,
    follow_redirects=True,
)

# Devuelve el cliente HTTP compartido para reutilización en repositorios
def get_supabase_http() -> httpx.AsyncClient:
    return _supabase_http


# Función auxiliar que intenta construir objetos pasando un cliente HTTP si es soportado
def _construct_maybe_with_client(ctor: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    # Intenta crear la instancia con el cliente HTTP para optimizar conexiones
    try:
        return ctor(*args, **kwargs)
    except TypeError as e:
        # Si el constructor no soporta 'client', lo crea sin él para compatibilidad
        if "client" in str(e) and ("unexpected keyword argument" in str(e) or "got an unexpected keyword" in str(e)):
            kwargs.pop("client", None)
            return ctor(*args, **kwargs)
        raise



# Instancias singleton de modelos de embeddings y cliente LLM para evitar recargas
_embeddings_model = EmbeddingsModel()
_llm_client = GeminiClient()


# RED 2 singleton
# Define la ruta absoluta al directorio del modelo RED2
_RED2_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "infrastructure", "ai", "red2_model")
)
# Carga el clasificador RED2 como singleton para reutilización
_red2_model = Red2Classifier(_RED2_DIR)


# RED 1 (singleton)
# Inicializa el clasificador RED1 con soporte para GPU si está disponible
_red1_classifier = Red1Classifier(
    settings.RED1_EXPORT_DIR,
    device="cuda" if torch.cuda.is_available() else "cpu",
)

# Crea el repositorio RED1 usando el cliente HTTP compartido si es soportado
_red1_repo = _construct_maybe_with_client(
    Red1RepoPostgrest,
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY,
    client=get_supabase_http(),  # ✅ pool compartido (si el repo lo soporta)
)

# Crea el servicio RED1 combinando clasificador y repositorio
_red1_service = Red1Service(_red1_classifier, _red1_repo)

# Devuelve el servicio RED1 singleton
def get_red1_service():
    return _red1_service


# RED 3 (singleton)
# Inicializa el clasificador RED3
_red3_classifier = Red3Classifier(settings.RED3_EXPORT_DIR)

# Crea el repositorio RED3 usando el cliente HTTP compartido
_red3_repo = _construct_maybe_with_client(
    Red3RepoPostgrest,
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY,
    client=get_supabase_http(),  
)

# Crea el servicio RED3 combinando clasificador y repositorio
_red3_service = Red3Service(_red3_repo, _red3_classifier)


# Clients
# Crea una instancia del cliente de autenticación usando el pool HTTP si es posible
def get_auth_client():
    return _construct_maybe_with_client(
        SupabaseAuthClient,
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        client=get_supabase_http(),
    )

# Crea una instancia del RPC para búsquedas semánticas con pool HTTP
def get_busqueda_rpc():
    return _construct_maybe_with_client(
        BusquedaSemanticaRPC,
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        client=get_supabase_http(),
    )

# Devuelve el cliente LLM singleton
def get_llm_client():
    return _llm_client


# Repositories
# Crea una instancia del repositorio de espacios con pool HTTP
def get_espacios_repo():
    return _construct_maybe_with_client(
        EspaciosRepo,
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        client=get_supabase_http(),
    )

# Crea una instancia del repositorio de chats de espacios con pool HTTP
def get_chat_espacios_repo():
    return _construct_maybe_with_client(
        ChatEspaciosRepo,
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        client=get_supabase_http(),
    )

# Crea una instancia del repositorio de embeddings con pool HTTP
def get_embeddings_repo():
    return _construct_maybe_with_client(
        EmbeddingsRepo,
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        client=get_supabase_http(),
    )

# Crea una instancia del repositorio RED2 con pool HTTP
def get_red2_repo():
    return _construct_maybe_with_client(
        Red2Repo,
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        client=get_supabase_http(),
    )

# Crea el servicio de guidance para RED2
def get_red2_guidance_service():
    return Red2GuidanceService(get_red2_repo())


# Use Cases
# Crea el caso de uso para crear un nuevo chat en un espacio de trabajo
def get_crear_chat_espacio_uc():
    return CrearChatEspacioUseCase(
        get_auth_client(),
        get_espacios_repo(),
        get_chat_espacios_repo(),
    )

# Crea el caso de uso para realizar búsquedas mixtas en espacios
def get_busqueda_mixta_uc():
    return BusquedaMixtaEspacioUseCase(
        get_auth_client(),
        _embeddings_model,
        get_busqueda_rpc(),
        get_espacios_repo(),
    )

# Crea el orquestador RAG para espacios, que combina búsqueda y generación
def get_orquestador_rag_espacio():
    return OrquestadorRAGEspacio(
        _embeddings_model,
        get_busqueda_rpc(),
    )

# Crea el caso de uso para enviar mensajes avanzados en espacios con recomendaciones
def get_enviar_mensaje_espacio_plus_uc():
    return EnviarMensajeEspacioPlusUseCase(
        get_auth_client(),
        get_espacios_repo(),
        get_chat_espacios_repo(),
        get_orquestador_rag_espacio(),
        get_llm_client(),
        get_red1_service(),
        red2_guidance_service=get_red2_guidance_service(),
        red3_service=get_red3_service(),  
    )

# Crea el caso de uso para ingestar archivos en espacios con clasificación IA
def get_ingestar_archivo_espacio_uc():
    return IngestarArchivoEspacioUseCase(
        get_auth_client(),
        get_espacios_repo(),
        _embeddings_model,
        get_embeddings_repo(),
        red1_service=get_red1_service(),
        red2_model=_red2_model,
        red2_repo=get_red2_repo(),
        red3_service=get_red3_service(),  
    )


# Use Cases EXTRA (GET list chats + GET historial chat)
# Crea el caso de uso para listar chats en un espacio validando permisos
def get_listar_chats_espacio_uc():
    # Lista conversaciones del espacio (validando espacio por RLS)
    return ListarChatsEspacioUseCase(
        get_espacios_repo(),
        get_chat_espacios_repo(),
    )

# Crea el caso de uso para obtener el historial de un chat en espacio
def get_historial_chat_espacio_uc():
    # Obtiene conversación + mensajes (validando espacio por RLS)
    return ObtenerChatEspacioUseCase(
        get_espacios_repo(),
        get_chat_espacios_repo(),
    )

# Alias para el historial de chat, para coincidir con nombres de rutas
def get_get_chat_espacio_history_uc():
    return get_historial_chat_espacio_uc()