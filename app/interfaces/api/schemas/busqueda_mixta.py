# app/interfaces/api/schemas/busqueda_mixta.py

# Este archivo define el esquema de Pydantic para solicitudes de búsqueda mixta.
# Incluye validaciones para texto, límites de resultados y ponderaciones.
# Utiliza Field para restricciones de longitud, rangos y valores por defecto.
# Forma parte de la validación de entrada en búsquedas semánticas y textuales.

# Librerías - Pydantic
from pydantic import BaseModel, Field

# Modelo Pydantic para solicitud de búsqueda mixta en espacios.
# Valida texto mínimo, límites de resultados docente y global, y ponderación.
class BusquedaMixtaRequest(BaseModel):
    # Texto de búsqueda, debe tener al menos 3 caracteres.
    texto: str = Field(..., min_length=3)
    # Número máximo de resultados por docente, entre 1 y 20, por defecto 5.
    top_k_docente: int = Field(default=5, ge=1, le=20)
    # Número máximo de resultados globales, entre 0 y 20, por defecto 3.
    top_k_global: int = Field(default=3, ge=0, le=20)
    # Ponderación para resultados del docente, entre 1.0 y 2.0, por defecto 1.25.
    ponderacion_docente: float = Field(default=1.25, ge=1.0, le=2.0)
