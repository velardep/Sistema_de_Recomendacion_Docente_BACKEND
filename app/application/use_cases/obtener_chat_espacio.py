# app/application/use_cases/obtener_chat_espacio.py

# Use case del flujo de ESPACIOS DE TRABAJO encargado de recuperar una
# conversación específica dentro de un espacio junto con todos sus mensajes.
# Primero valida que el espacio exista, luego obtiene la conversación y
# finalmente consulta el historial completo de mensajes asociado.

class ObtenerChatEspacioUseCase:
    def __init__(self, espacios_repo, chat_espacios_repo):
        self.espacios_repo = espacios_repo
        self.chat_espacios_repo = chat_espacios_repo

    async def execute(self, access_token: str, espacio_id: str, conversacion_espacio_id: str):
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return None
        # Recupera la conversación específica del espacio; si no existe se detiene el flujo.
        conv = await self.chat_espacios_repo.obtener_conversacion(access_token, conversacion_espacio_id)
        if not conv:
            return None
        # Obtiene todos los mensajes asociados a la conversación para devolver el historial completo.
        msgs = await self.chat_espacios_repo.listar_mensajes(access_token, conversacion_espacio_id)
        return {"conversation": conv, "messages": msgs}
