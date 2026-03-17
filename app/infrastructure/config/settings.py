# app/infrastructure/config/settings.py

# Este archivo configura las variables de entorno y ajustes globales de la aplicación.
# Utiliza Pydantic BaseSettings para validar y cargar configuraciones desde .env.
# Define rutas de modelos, claves API y flags de funcionalidades del sistema.
# Centraliza la configuración para acceso consistente en toda la aplicación.

# Librerías - Sistema de archivos
from pathlib import Path

# Librerías - Configuración
from pydantic_settings import BaseSettings

# Definición de directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Clase de configuración principal que hereda de BaseSettings.
# Carga variables de entorno con validación automática.
class Settings(BaseSettings):
    # Configuración de Supabase para base de datos y autenticación
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    
    # Clave API para Gemini LLM
    GEMINI_API_KEY: str

    # Directorios de exportación para modelos de IA
    RED1_EXPORT_DIR: str = str(BASE_DIR / "infrastructure" / "ai" / "red1_model")
    RED2_EXPORT_DIR: str = str(BASE_DIR / "infrastructure" / "ai" / "red2_model")
    RED3_EXPORT_DIR: str = str(BASE_DIR / "infrastructure" / "ai" / "red3_model")

    # Flags para habilitar/deshabilitar funcionalidades del PDC
    pdc_enable_red1: bool = True
    pdc_enable_rag: bool = True
    pdc_enable_red2: bool = True

    # Buckets de almacenamiento para biblioteca PDC y archivos de espacios
    PDC_LIBRARY_BUCKET: str = "pdc-library"
    ESPACIO_FILES_BUCKET: str = "espacio-files"

    # R2
    R2_ENDPOINT: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET: str | None = None
    R2_MODELS_PREFIX: str = "models"

    RED1_R2_PREFIX: str = "models/red1"
    RED2_R2_PREFIX: str = "models/red2"
    RED3_R2_PREFIX: str = "models/red3"

    model_config = {
        "env_file": ".env"
    }

settings = Settings()
