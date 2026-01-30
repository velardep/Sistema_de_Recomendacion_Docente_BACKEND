from pydantic import BaseModel, Field
from typing import Optional

class CrearChatEspacioRequest(BaseModel):
    titulo: Optional[str] = Field(default="Chat del espacio", min_length=2)

class EnviarMensajeEspacioPlusRequest(BaseModel):
    conversacion_espacio_id: str = Field(..., min_length=10)
    content: str = Field(..., min_length=1)

class BusquedaMixtaRequest(BaseModel):
    texto: str = Field(..., min_length=3)
    top_k_docente: int = Field(default=5, ge=1, le=20)
    top_k_global: int = Field(default=3, ge=0, le=20)
    ponderacion_docente: float = Field(default=1.25, ge=1.0, le=2.0)
