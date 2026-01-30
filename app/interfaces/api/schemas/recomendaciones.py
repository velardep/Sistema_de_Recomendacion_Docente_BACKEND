from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CrearRecomendacionRequest(BaseModel):
    conversacion_id: Optional[str] = None
    mensaje_id: Optional[str] = None
    tipo: str = Field(..., pattern="^(estrategia|recurso|redaccion|otro)$")
    modelo: Optional[str] = "mock"
    contenido: str = Field(..., min_length=1)
    metadatos: Dict[str, Any] = {}

class RegistrarAccionRequest(BaseModel):
    accion: str = Field(..., pattern="^(aceptar|rechazar|editar|solicitar_mas_detalle|copiar|calificar)$")
    valor: Optional[float] = None
    comentario: Optional[str] = None
    metadatos: Dict[str, Any] = {}
