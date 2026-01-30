# app/application/use_cases/obtener_chat_espacio.py
class ObtenerChatEspacioUseCase:
    def __init__(self, espacios_repo, chat_espacios_repo):
        self.espacios_repo = espacios_repo
        self.chat_espacios_repo = chat_espacios_repo

    async def execute(self, access_token: str, espacio_id: str, conversacion_espacio_id: str):
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return None

        conv = await self.chat_espacios_repo.obtener_conversacion(access_token, conversacion_espacio_id)
        if not conv:
            return None

        msgs = await self.chat_espacios_repo.listar_mensajes(access_token, conversacion_espacio_id)
        return {"conversation": conv, "messages": msgs}
