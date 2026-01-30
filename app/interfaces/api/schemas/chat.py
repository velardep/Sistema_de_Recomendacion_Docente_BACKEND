from pydantic import BaseModel, Field
from typing import Optional

class CreateChatRequest(BaseModel):
    titulo: Optional[str] = None

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
