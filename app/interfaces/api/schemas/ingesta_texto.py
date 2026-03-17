# app/interfaces/api/schemas/ingesta_texto.py

# Este archivo define el esquema de Pydantic para la ingesta de texto en espacios.
# Incluye modelo para procesar texto con configuraciones de chunking y overlap.
# Utiliza Field para validaciones de longitud, rangos y valores por defecto.
# Forma parte de la validación de entrada en endpoints de ingesta de contenido.

# Librerías - Pydantic
from pydantic import BaseModel, Field

# Librerías - Tipos
from typing import Optional

# Modelo Pydantic para solicitud de ingesta de texto.
# Valida texto mínimo 50 caracteres, con configuraciones opcionales de chunking.
class IngestarTextoRequest(BaseModel):
    titulo: Optional[str] = None
    texto: str = Field(..., min_length=50)  
    tam_chunk: int = Field(default=900, ge=300, le=2000)
    overlap: int = Field(default=120, ge=0, le=400)
