from pydantic import BaseModel, Field
from typing import Optional

class CrearEspacioRequest(BaseModel):
    nombre: str = Field(..., min_length=2)
    nivel: Optional[str] = None
    grado: Optional[str] = None
    materia: Optional[str] = None
    descripcion: Optional[str] = None

class ActualizarEspacioRequest(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2)
    nivel: Optional[str] = None
    grado: Optional[str] = None
    materia: Optional[str] = None
    descripcion: Optional[str] = None
