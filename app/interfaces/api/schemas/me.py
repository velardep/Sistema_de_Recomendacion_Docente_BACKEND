# app/interfaces/api/schemas/me.py

# Este archivo define el esquema de Pydantic para la gestión del perfil de usuario.
# Incluye modelo para actualizar información personal y preferencias del docente.
# Utiliza tipos opcionales y diccionarios para campos flexibles.
# Forma parte de la validación de entrada en endpoints de perfil de usuario.

# Librerías - Pydantic
from pydantic import BaseModel

# Librerías - Tipos
from typing import Optional, Dict, Any

# Modelo Pydantic para solicitud de actualización de perfil de usuario.
# Valida nombres y apellidos obligatorios, con campos opcionales para información docente.
class UpsertMeRequest(BaseModel):
    nombres: str
    apellidos: str
    unidad_educativa: Optional[str] = None
    nivel: Optional[str] = None
    grado: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    preferencias: Dict[str, Any] = {}
