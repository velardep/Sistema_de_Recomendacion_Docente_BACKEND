from pydantic import BaseModel, Field
from typing import Optional

class BusquedaSemanticaRequest(BaseModel):
    texto: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    tipo_fuente: Optional[str] = Field(default="prontuario")  # prontuario|archivo|pdc|otro
    espacio_id: Optional[str] = None
