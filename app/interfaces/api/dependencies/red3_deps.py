# app/interfaces/api/dependencies/red3_deps.py

# Este archivo gestiona las dependencias de inyección para los componentes relacionados con RED3.
# Proporciona funciones que crean instancias de repositorios, clasificadores, servicios y clientes
# necesarios para el procesamiento de recomendaciones y análisis con la red neuronal RED3.
# Incluye integración con Supabase para persistencia, modelos de IA y cliente LLM para recomendaciones avanzadas.

# Infraestructura - Configuración
from app.infrastructure.config.settings import settings

# Infraestructura - Persistencia - RED3
from app.infrastructure.persistence.supabase.red3_repo import Red3RepoPostgrest
from app.infrastructure.persistence.supabase.red3_llm_recs_repo import Red3LlmRecsRepoPostgrest

# Infraestructura - IA - Clasificadores RED
from app.infrastructure.ai.red3_classifier import Red3Classifier

# Infraestructura - Seguridad
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient

# Infraestructura - LLM
from app.infrastructure.llm.gemini_client import GeminiClient

# Aplicación - Servicios
from app.application.services.red3_service import Red3Service

# Función que crea y retorna un cliente de autenticación de Supabase.
# Utiliza la URL y clave anónima de Supabase para manejar autenticación.
def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Función que crea y retorna el repositorio para datos de RED3.
# Configura el repositorio con credenciales de Supabase para acceso a datos.
def get_red3_repo():
    return Red3RepoPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Función que crea y retorna el clasificador RED3.
# Inicializa el clasificador con el directorio de exportación especificado en settings.
def get_red3_classifier():
    return Red3Classifier(settings.RED3_EXPORT_DIR)

# Función que crea y retorna el servicio RED3.
# Combina el repositorio y clasificador para proporcionar funcionalidades de análisis.
def get_red3_service():
    return Red3Service(get_red3_repo(), get_red3_classifier())

# Instancia singleton del cliente LLM para evitar recargas costosas.
# Se crea una vez y se reutiliza en todas las llamadas.
_llm_client = GeminiClient()

# Función que retorna la instancia singleton del cliente LLM.
# Proporciona acceso al modelo de lenguaje para generar recomendaciones.
def get_llm_client():
    return _llm_client

# Función que crea y retorna el repositorio para recomendaciones LLM de RED3.
# Configura el repositorio con credenciales de Supabase para almacenar recomendaciones.
def get_red3_llm_recs_repo():
    return Red3LlmRecsRepoPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)