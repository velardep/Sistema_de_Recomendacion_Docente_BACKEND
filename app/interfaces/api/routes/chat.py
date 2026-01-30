from fastapi import APIRouter, Depends, HTTPException, Header
from app.interfaces.api.schemas.chat import CreateChatRequest, SendMessageRequest
from app.interfaces.api.dependencies.chat_deps import (
    get_create_chat_uc, get_list_chats_uc, get_get_history_uc, get_send_message_uc
)
from app.application.use_cases.create_chat import CreateChatUseCase
from app.application.use_cases.list_chats import ListChatsUseCase
from app.application.use_cases.get_chat_history import GetChatHistoryUseCase
from app.application.use_cases.send_message import SendMessageUseCase

router = APIRouter(prefix="/chats", tags=["chats"])

def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Use: Bearer <token>")
    return authorization.split(" ", 1)[1].strip()

@router.post("")
async def create_chat(
    req: CreateChatRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: CreateChatUseCase = Depends(get_create_chat_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, req.titulo)

@router.get("")
async def list_chats(
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: ListChatsUseCase = Depends(get_list_chats_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token)

@router.get("/{chat_id}")
async def get_chat_history(
    chat_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: GetChatHistoryUseCase = Depends(get_get_history_uc),
):
    token = extract_bearer_token(authorization)
    data = await uc.execute(token, chat_id)
    if not data:
        raise HTTPException(status_code=404, detail="Chat not found")
    return data

@router.post("/{chat_id}/messages")
async def send_message(
    chat_id: str,
    req: SendMessageRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: SendMessageUseCase = Depends(get_send_message_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, chat_id, req.content)



from app.application.use_cases.enviar_mensaje_con_recomendaciones import EnviarMensajeConRecomendacionesUseCase
from app.interfaces.api.dependencies.chat_deps import get_enviar_mensaje_con_recomendaciones_uc

@router.post("/{chat_id}/messages-plus")
async def send_message_plus(
    chat_id: str,
    req: SendMessageRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: EnviarMensajeConRecomendacionesUseCase = Depends(get_enviar_mensaje_con_recomendaciones_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, chat_id, req.content)
