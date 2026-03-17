# app/interfaces/api/dependencies/pdc_deps.py

# Este archivo gestiona las dependencias para la generación de PDC (Plan de Desarrollo Curricular).
# Centraliza la creación de singletons para modelos de IA, clasificadores de redes neuronales,
# repositorios de datos y el caso de uso principal para generar documentos PDC.
# Integra múltiples servicios RED para análisis y recomendaciones.
# Facilita la inyección de dependencias en las rutas de generación de PDC de la API.

# Librerías estándar
import torch

# Configuración del sistema
from app.infrastructure.config.settings import settings

# Infraestructura - Seguridad
from app.infrastructure.security.supabase_auth_client import SupabaseAuthClient

# Infraestructura - IA - Embeddings
from app.infrastructure.ai.embeddings_model import EmbeddingsModel

# Infraestructura - Persistencia - RPC
from app.infrastructure.persistence.supabase.busqueda_semantica_rpc import BusquedaSemanticaRPC

# Infraestructura - IA - Clasificadores RED
from app.infrastructure.ai.red1_classifier import Red1Classifier
from app.infrastructure.ai.red3_classifier import Red3Classifier

# Infraestructura - Persistencia - Repositorios RED
from app.infrastructure.persistence.supabase.red1_repo import Red1RepoPostgrest
from app.infrastructure.persistence.supabase.red2_repo import Red2Repo
from app.infrastructure.persistence.supabase.red3_repo import Red3RepoPostgrest

# Aplicación - Servicios RED
from app.application.services.red1_service import Red1Service
from app.application.services.red2_guidance import Red2GuidanceService
from app.application.services.red3_service import Red3Service

# Infraestructura - LLM
from app.infrastructure.llm.gemini_client import GeminiClient

# Aplicación - Casos de uso
from app.application.use_cases.generate_pdc import GeneratePdcUseCase

# Infraestructura - Persistencia - PDC
from app.infrastructure.persistence.supabase.pdc_repository_postgrest import PdcRepositoryPostgrest

# Dependencias externas de otros módulos de dependencias
from app.interfaces.api.dependencies.red3_deps import get_red3_service


# Singletons 
# Instancias singleton de modelos y servicios para evitar recargas costosas
_embeddings_model = EmbeddingsModel()
_busqueda_rpc = BusquedaSemanticaRPC(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
_pdc_repo = PdcRepositoryPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
_llm_client = GeminiClient()

# Inicializa el clasificador RED1 con soporte para GPU si está disponible
_red1_classifier = Red1Classifier(
    settings.RED1_EXPORT_DIR,
    device="cuda" if torch.cuda.is_available() else "cpu"
)
# Crea el repositorio y servicio RED1
_red1_repo = Red1RepoPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
_red1_service = Red1Service(_red1_classifier, _red1_repo)

# Crea el repositorio y servicio de guidance para RED2
_red2_repo = Red2Repo(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
_red2_guidance_service = Red2GuidanceService(_red2_repo)

# Inicializa el clasificador, repositorio y servicio RED3
_red3_classifier = Red3Classifier(settings.RED3_EXPORT_DIR)
_red3_repo = Red3RepoPostgrest(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
_red3_service = Red3Service(_red3_repo, _red3_classifier)


# Clients
# Crea y devuelve una instancia del cliente de autenticación de Supabase
def get_auth_client():
    return SupabaseAuthClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


# Use Case
# Crea y devuelve el caso de uso para generar PDC, integrando múltiples servicios
def get_generate_pdc_uc():
    return GeneratePdcUseCase(
        get_auth_client(),
        _embeddings_model,
        _busqueda_rpc,
        _red1_service,
        _red2_guidance_service,
        _pdc_repo,          
        _llm_client,
        red3_service=get_red3_service(), 
    )