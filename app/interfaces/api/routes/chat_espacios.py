# app/interfaces/api/routes/chat_espacios.py

# Este archivo define las rutas de la API para gestión de chats en espacios de trabajo.
# Incluye endpoints para listar chats, obtener historial, crear chats, enviar mensajes avanzados,
# realizar búsquedas mixtas y subir archivos, todos integrados con casos de uso.
# Maneja autenticación vía tokens Bearer y errores de recursos no encontrados.

# Futuro
from __future__ import annotations

# Framework - FastAPI
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File

# Interfaces - Utilidades de rutas
from app.interfaces.api.routes.busqueda import extract_bearer_token

# Interfaces - Esquemas de API
from app.interfaces.api.schemas.chat_espacios import (
    CrearChatEspacioRequest,
    EnviarMensajeEspacioPlusRequest,
    BusquedaMixtaRequest,
)

# Interfaces - Dependencias
from app.interfaces.api.dependencies.chat_espacio_deps import (
    get_crear_chat_espacio_uc,
    get_enviar_mensaje_espacio_plus_uc,
    get_busqueda_mixta_uc,
    get_listar_chats_espacio_uc,
    get_historial_chat_espacio_uc,
    get_ingestar_archivo_espacio_uc,
)

# Creación del router para rutas de espacios con prefijo /espacios y etiqueta chat-espacios.
router = APIRouter(prefix="/espacios", tags=["chat-espacios"])

# Endpoint GET para listar chats en un espacio.
# Extrae token y ejecuta el caso de uso para obtener la lista.
@router.get("/{espacio_id}/chat")
async def listar_chats_espacio(
    espacio_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_listar_chats_espacio_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id)

# Endpoint GET para obtener historial de un chat específico en un espacio.
# Extrae token, ejecuta el caso de uso y verifica si el chat existe.
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

# Endpoint POST para crear un nuevo chat en un espacio.
# Extrae token, ejecuta el caso de uso con título y verifica existencia del espacio.
@router.post("/{espacio_id}/chat")
async def crear_chat_espacio(
    espacio_id: str,
    req: CrearChatEspacioRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_crear_chat_espacio_uc),
):
    token = extract_bearer_token(authorization)
    result = await uc.execute(token, espacio_id, req.titulo)
    if not result:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    return result

# Endpoint POST para enviar mensaje avanzado en un chat de espacio.
# Extrae token, ejecuta el caso de uso con contenido y verifica recursos.
@router.post("/{espacio_id}/chat/messages-plus")
async def enviar_mensaje_espacio_plus(
    espacio_id: str,
    req: EnviarMensajeEspacioPlusRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_enviar_mensaje_espacio_plus_uc),
):
    token = extract_bearer_token(authorization)
    result = await uc.execute(token, espacio_id, req.conversacion_espacio_id, req.content)
    if not result:
        raise HTTPException(status_code=404, detail="Espacio o conversación no encontrada")
    return result

# Endpoint POST para búsqueda mixta en un espacio.
# Extrae token y ejecuta el caso de uso con datos de búsqueda.
@router.post("/{espacio_id}/busqueda-mixta")
async def busqueda_mixta(
    espacio_id: str,
    req: BusquedaMixtaRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_busqueda_mixta_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id, req.model_dump())

# Endpoint POST para subir archivo a un espacio.
# Extrae token y ejecuta el caso de uso con el archivo subido.
@router.post("/{espacio_id}/archivos")
async def subir_archivo_espacio(
    espacio_id: str,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc=Depends(get_ingestar_archivo_espacio_uc),
):
    token = extract_bearer_token(authorization)
    return await uc.execute(token, espacio_id, file)