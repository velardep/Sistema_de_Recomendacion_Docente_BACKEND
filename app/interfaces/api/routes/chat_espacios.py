# app/interfaces/api/routes/chat_espacios.py
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from app.interfaces.api.routes.busqueda import extract_bearer_token
from app.interfaces.api.schemas.chat_espacios import (
    CrearChatEspacioRequest,
    EnviarMensajeEspacioPlusRequest,
    BusquedaMixtaRequest
)
from app.interfaces.api.dependencies.chat_espacio_deps import (
    get_crear_chat_espacio_uc,
    get_enviar_mensaje_espacio_plus_uc,
    get_busqueda_mixta_uc,
    get_listar_chats_espacio_uc,      # ✅ nuevo
    get_historial_chat_espacio_uc,    # ✅ nuevo
    get_ingestar_archivo_espacio_uc,  # ✅ ya lo estabas usando
    get_get_chat_espacio_history_uc,
)

router = APIRouter(prefix="/espacios", tags=["chat-espacios"])


@router.get("/{espacio_id}/chat")
async def listar_chats_espacio(
    espacio_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_listar_chats_espacio_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id)

@router.get("/{espacio_id}/chat/{conversacion_espacio_id}")
async def obtener_historial_chat_espacio(
    espacio_id: str,
    conversacion_espacio_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_get_chat_espacio_history_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id, conversacion_espacio_id)



@router.get("/{espacio_id}/chat")
async def listar_chats_espacio(
    espacio_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_listar_chats_espacio_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id)

@router.get("/{espacio_id}/chat/{conversacion_espacio_id}")
async def obtener_historial_chat_espacio(
    espacio_id: str,
    conversacion_espacio_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_historial_chat_espacio_uc),
):
    token = extract_bearer_token(authorization)
    data = await uc.execute(token, espacio_id, conversacion_espacio_id)
    if not data:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    return data

@router.post("/{espacio_id}/chat")
async def crear_chat_espacio(
    espacio_id: str,
    req: CrearChatEspacioRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_crear_chat_espacio_uc)
):
    token = extract_bearer_token(authorization)
    result = await uc.execute(token, espacio_id, req.titulo)
    if not result:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    return result

@router.post("/{espacio_id}/chat/messages-plus")
async def enviar_mensaje_espacio_plus(
    espacio_id: str,
    req: EnviarMensajeEspacioPlusRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_enviar_mensaje_espacio_plus_uc)
):
    token = extract_bearer_token(authorization)
    result = await uc.execute(token, espacio_id, req.conversacion_espacio_id, req.content)
    if not result:
        raise HTTPException(status_code=404, detail="Espacio o conversación no encontrada")
    return result

@router.post("/{espacio_id}/busqueda-mixta")
async def busqueda_mixta(
    espacio_id: str,
    req: BusquedaMixtaRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_busqueda_mixta_uc)
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id, req.model_dump())

@router.post("/{espacio_id}/archivos")
async def subir_archivo_espacio(
    espacio_id: str,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_ingestar_archivo_espacio_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id, file)
