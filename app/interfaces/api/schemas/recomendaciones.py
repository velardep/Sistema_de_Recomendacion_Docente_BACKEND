# app/interfaces/api/schemas/recomendaciones.py

# Este archivo define los esquemas de Pydantic para la gestión de recomendaciones.
# Incluye modelos para crear recomendaciones y registrar acciones sobre ellas.
# Utiliza Field para validaciones de patrones, longitud y valores por defecto.
# Forma parte de la validación de entrada en endpoints de recomendaciones pedagógicas.

# Librerías - Pydantic
from pydantic import BaseModel, Field

# Librerías - Tipos
from typing import Optional, Dict, Any

# Modelo Pydantic para solicitud de creación de recomendación.
# Valida tipo con patrón específico, contenido mínimo y metadatos opcionales.
class CrearRecomendacionRequest(BaseModel):
    conversacion_id: Optional[str] = None
    mensaje_id: Optional[str] = None
    tipo: str = Field(..., pattern="^(estrategia|recurso|redaccion|otro)$")
    modelo: Optional[str] = "mock"
    contenido: str = Field(..., min_length=1)
    metadatos: Dict[str, Any] = {}

# Modelo Pydantic para solicitud de registro de acción sobre recomendación.
# Valida acción con patrón específico, con valor y comentario opcionales.
class RegistrarAccionRequest(BaseModel):
    accion: str = Field(..., pattern="^(aceptar|rechazar|editar|solicitar_mas_detalle|copiar|calificar)$")
    valor: Optional[float] = None
    comentario: Optional[str] = None
    metadatos: Dict[str, Any] = {}
