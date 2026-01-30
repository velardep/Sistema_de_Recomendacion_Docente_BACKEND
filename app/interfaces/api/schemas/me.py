from pydantic import BaseModel
from typing import Optional, Dict, Any

class UpsertMeRequest(BaseModel):
    nombres: str
    apellidos: str
    unidad_educativa: Optional[str] = None
    nivel: Optional[str] = None
    grado: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    preferencias: Dict[str, Any] = {}
