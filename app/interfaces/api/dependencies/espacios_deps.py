# app/interfaces/api/dependencies/espacios_deps.py

# Este archivo gestiona las dependencias para la gestión de espacios de trabajo.
# Proporciona funciones para crear, listar, obtener, actualizar y eliminar espacios,
# así como para ingestar textos en espacios con generación de embeddings.
# Utiliza repositorios para persistencia y modelos de IA para procesamiento de texto.
# Facilita la inyección de dependencias en las rutas de gestión de espacios de la API.

# Configuración del sistema
from app.infrastructure.config.settings import settings

# Infraestructura - Seguridad
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient

# Infraestructura - Persistencia - Espacios
from app.infrastructure.persistence.supabase.espacios_repo import EspaciosRepo

# Aplicación - Casos de uso - Gestión de espacios
from app.application.use_cases.crear_espacio import CrearEspacioUseCase
from app.application.use_cases.listar_espacios import ListarEspaciosUseCase
from app.application.use_cases.obtener_espacio import ObtenerEspacioUseCase
from app.application.use_cases.actualizar_espacio import ActualizarEspacioUseCase
from app.application.use_cases.eliminar_espacio import EliminarEspacioUseCase

# Infraestructura - IA - Embeddings
from app.infrastructure.ai.embeddings_model import EmbeddingsModel

# Infraestructura - Persistencia - Textos y embeddings
from app.infrastructure.persistence.supabase.textos_espacio_repo import TextosEspacioRepo
from app.infrastructure.persistence.supabase.embeddings_repo import EmbeddingsRepo

# Aplicación - Casos de uso - Ingesta de texto
from app.application.use_cases.ingestar_texto_espacio import IngestarTextoEspacioUseCase



# Crea y devuelve una instancia del cliente de autenticación de Supabase
def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del repositorio de espacios
def get_espacios_repo():
    return EspaciosRepo(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve el caso de uso para crear un nuevo espacio
def get_crear_espacio_uc():
    return CrearEspacioUseCase(get_auth_client(), get_espacios_repo())

# Crea y devuelve el caso de uso para listar espacios
def get_listar_espacios_uc():
    return ListarEspaciosUseCase(get_espacios_repo())

# Crea y devuelve el caso de uso para obtener un espacio específico
def get_obtener_espacio_uc():
    return ObtenerEspacioUseCase(get_espacios_repo())

# Crea y devuelve el caso de uso para actualizar un espacio
def get_actualizar_espacio_uc():
    return ActualizarEspacioUseCase(get_espacios_repo())

# Crea y devuelve el caso de uso para eliminar un espacio
def get_eliminar_espacio_uc():
    return EliminarEspacioUseCase(get_espacios_repo())

# Instancia singleton del modelo de embeddings para reutilización
_embeddings_model = EmbeddingsModel()

# Crea y devuelve una instancia del repositorio de textos de espacios
def get_textos_repo():
    return TextosEspacioRepo(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve una instancia del repositorio de embeddings
def get_embeddings_repo():
    return EmbeddingsRepo(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Crea y devuelve el caso de uso para ingestar texto en un espacio con embeddings
def get_ingestar_texto_uc():
    return IngestarTextoEspacioUseCase(
        get_auth_client(),
        get_espacios_repo(),
        get_textos_repo(),
        get_embeddings_repo(),
        _embeddings_model
    )

