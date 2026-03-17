# app/interfaces/api/schemas/busqueda.py

# Este archivo define el esquema de Pydantic para solicitudes de búsqueda semántica.
# Incluye validaciones para texto, número de resultados, tipo de fuente y espacio.
# Utiliza Field para restricciones y Optional para campos opcionales.
# Forma parte de la validación de entrada en búsquedas basadas en embeddings.

# Librerías - Pydantic
from pydantic import BaseModel, Field

# Librerías estándar - Typing
from typing import Optional

# Modelo Pydantic para solicitud de búsqueda semántica.
# Valida texto mínimo, límites de resultados, tipo de fuente opcional y espacio opcional.
class BusquedaSemanticaRequest(BaseModel):
    # Texto de búsqueda, debe tener al menos 1 caracter.
    texto: str = Field(..., min_length=1)
    # Número máximo de resultados, entre 1 y 20, por defecto 5.
    top_k: int = Field(default=5, ge=1, le=20)
    # Tipo de fuente opcional, por defecto "prontuario" (prontuario|archivo|pdc|otro).
    tipo_fuente: Optional[str] = Field(default="prontuario")  
    # ID del espacio opcional para búsquedas en espacios específicos.
    espacio_id: Optional[str] = None
