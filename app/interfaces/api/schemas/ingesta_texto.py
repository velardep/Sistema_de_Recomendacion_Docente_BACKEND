from pydantic import BaseModel, Field
from typing import Optional

class IngestarTextoRequest(BaseModel):
    titulo: Optional[str] = None
    texto: str = Field(..., min_length=50)  # evita basura
    tam_chunk: int = Field(default=900, ge=300, le=2000)
    overlap: int = Field(default=120, ge=0, le=400)
