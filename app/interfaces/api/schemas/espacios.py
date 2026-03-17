# app/interfaces/api/schemas/espacios.py

# Este archivo define los esquemas de Pydantic para la gestión de espacios de trabajo.
# Incluye modelos para crear y actualizar espacios con campos opcionales para metadata.
# Utiliza Field para validaciones de longitud en el nombre requerido.
# Forma parte de la validación de entrada en los endpoints de espacios.

# Librerías - Pydantic
from pydantic import BaseModel, Field

# Librerías - Tipos
from typing import Optional

# Modelo Pydantic para solicitud de creación de espacio de trabajo.
class CrearEspacioRequest(BaseModel):
    nombre: str = Field(..., min_length=2)
    nivel: Optional[str] = None
    grado: Optional[str] = None
    materia: Optional[str] = None
    descripcion: Optional[str] = None

# Permite actualizar campos opcionalmente, con validación en nombre si se proporciona.
class ActualizarEspacioRequest(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2)
    nivel: Optional[str] = None
    grado: Optional[str] = None
    materia: Optional[str] = None
    descripcion: Optional[str] = None
