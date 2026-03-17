# app/interfaces/api/routes/chat.py

# Este archivo define las rutas de la API para gestión de chats generales.
# Incluye endpoints para crear chats, listar chats, obtener historial, enviar mensajes simples
# y enviar mensajes con recomendaciones, utilizando casos de uso para la lógica.
# Maneja autenticación vía tokens Bearer y errores de recursos no encontrados.

# Framework - FastAPI
from fastapi import APIRouter, Depends, HTTPException, Header

# Interfaces - Esquemas de API
from app.interfaces.api.schemas.chat import CreateChatRequest, SendMessageRequest

# Interfaces - Dependencias
from app.interfaces.api.dependencies.chat_deps import (
    get_create_chat_uc, get_list_chats_uc, get_get_history_uc, get_send_message_uc,
    get_enviar_mensaje_con_recomendaciones_uc
)

# Aplicación - Casos de uso
from app.application.use_cases.create_chat import CreateChatUseCase
from app.application.use_cases.list_chats import ListChatsUseCase
from app.application.use_cases.get_chat_history import GetChatHistoryUseCase
from app.application.use_cases.send_message import SendMessageUseCase
from app.application.use_cases.enviar_mensaje_con_recomendaciones import EnviarMensajeConRecomendacionesUseCase

# Creación del router para rutas de chats con prefijo /chats y etiqueta chats.
router = APIRouter(prefix="/chats", tags=["chats"])

# Función utilitaria para extraer el token Bearer del header de autorización.
# Valida que el header exista y comience con "Bearer", luego extrae el token.
def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Use: Bearer <token>")
    return authorization.split(" ", 1)[1].strip()

# Endpoint POST para crear un nuevo chat.
# Extrae token y ejecuta el caso de uso con el título proporcionado.
@router.post("")
async def create_chat(
    req: CreateChatRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: CreateChatUseCase = Depends(get_create_chat_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, req.titulo)

# Endpoint GET para listar todos los chats del usuario.
# Extrae token y ejecuta el caso de uso para obtener la lista.
@router.get("")
async def list_chats(
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: ListChatsUseCase = Depends(get_list_chats_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token)

# Endpoint GET para obtener el historial de un chat específico.
# Extrae token, ejecuta el caso de uso y verifica si hay datos.
@router.get("/{chat_id}")
async def get_chat_history(
    chat_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: GetChatHistoryUseCase = Depends(get_get_history_uc),
):
    token = extract_bearer_token(authorization)
    data = await uc.execute(token, chat_id)
    if not data:
        raise HTTPException(status_code=404, detail="Cuenta sin chats, inicie uno nuevo")
    return data

# Endpoint POST para enviar un mensaje simple a un chat.
# Extrae token y ejecuta el caso de uso con el contenido del mensaje.
@router.post("/{chat_id}/messages")
async def send_message(
    chat_id: str,
    req: SendMessageRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: SendMessageUseCase = Depends(get_send_message_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, chat_id, req.content)

# Endpoint POST para enviar un mensaje con recomendaciones a un chat.
# Extrae token y ejecuta el caso de uso avanzado con el contenido.
@router.post("/{chat_id}/messages-plus")
async def send_message_plus(
    chat_id: str,
    req: SendMessageRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: EnviarMensajeConRecomendacionesUseCase = Depends(get_enviar_mensaje_con_recomendaciones_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, chat_id, req.content)
