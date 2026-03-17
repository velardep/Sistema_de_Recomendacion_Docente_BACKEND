# app/interfaces/api/schemas/chat.py

# Este archivo define los esquemas de Pydantic para la gestión de chats generales.
# Incluye modelos para crear chats y enviar mensajes en conversaciones estándar.
# Utiliza Field para validaciones de longitud en los campos requeridos.
# Forma parte de la validación de entrada en los endpoints de chat.

# Librerías - Pydantic
from pydantic import BaseModel, Field

# Librerías - Tipos
from typing import Optional

# Modelo Pydantic para solicitud de creación de chat general.
# Valida título opcional sin restricciones específicas.
class CreateChatRequest(BaseModel):
    titulo: Optional[str] = None

# Valida que el contenido tenga al menos 1 caracter.
class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
