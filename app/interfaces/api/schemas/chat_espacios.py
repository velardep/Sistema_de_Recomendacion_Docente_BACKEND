# app/interfaces/api/schemas/chat_espacios.py

# Este archivo define los esquemas de Pydantic para la gestión de chats en espacios.
# Incluye modelos para crear chats, enviar mensajes con recomendaciones y búsquedas mixtas.
# Utiliza Field para validaciones de longitud y rangos en los campos requeridos.
# Forma parte de la validación de entrada en los endpoints de espacios de trabajo.

# Librerías - Pydantic
from pydantic import BaseModel, Field

# Librerías - Tipos
from typing import Optional

# Modelo Pydantic para solicitud de creación de chat en espacio.
# Valida título opcional con mínimo 2 caracteres.
class CrearChatEspacioRequest(BaseModel):
    titulo: Optional[str] = Field(default="Chat del espacio", min_length=2)

# Valida ID de conversación y contenido del mensaje.
class EnviarMensajeEspacioPlusRequest(BaseModel):
    conversacion_espacio_id: str = Field(..., min_length=10)
    content: str = Field(..., min_length=1)

# Valida texto, límites de resultados y ponderación.
class BusquedaMixtaRequest(BaseModel):
    texto: str = Field(..., min_length=3)
    top_k_docente: int = Field(default=5, ge=1, le=20)
    top_k_global: int = Field(default=3, ge=0, le=20)
    ponderacion_docente: float = Field(default=1.25, ge=1.0, le=2.0)
