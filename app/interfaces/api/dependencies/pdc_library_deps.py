# app/interfaces/api/dependencies/pdc_library_deps.py

# Este archivo contiene las dependencias de inyección para el repositorio de la biblioteca PDC.
# Proporciona funciones que crean instancias del repositorio PDC Library,
# configuradas con las credenciales de Supabase y el bucket especificado.
# Facilita la gestión de archivos y recursos en la biblioteca PDC de manera centralizada.

# Infraestructura - Configuración
from app.infrastructure.config.settings import settings

# Infraestructura - Persistencia - PDC Library
from app.infrastructure.pdc_library.pdc_library_repo import PdcLibraryRepo

# Función que crea y retorna una instancia del repositorio PDC Library.
# Configura el repositorio con la URL de Supabase, clave anónima y bucket PDC.
def get_pdc_library_repo() -> PdcLibraryRepo:
    return PdcLibraryRepo(
        supabase_url=settings.SUPABASE_URL,
        anon_key=settings.SUPABASE_ANON_KEY,
        bucket=settings.PDC_LIBRARY_BUCKET,
    )