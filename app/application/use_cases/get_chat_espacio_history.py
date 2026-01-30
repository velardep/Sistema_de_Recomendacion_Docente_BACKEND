class GetChatEspacioHistoryUseCase:
    def __init__(self, chat_espacios_repo):
        self.chat_espacios_repo = chat_espacios_repo

    async def execute(self, access_token: str, espacio_id: str, conversacion_espacio_id: str):
        conv = await self.chat_espacios_repo.obtener_conversacion(access_token, conversacion_espacio_id)
        if not conv:
            return None

        # extra guard: conv debe pertenecer al espacio solicitado
        if str(conv.get("espacio_id")) != str(espacio_id):
            return None

        msgs = await self.chat_espacios_repo.listar_mensajes(access_token, conversacion_espacio_id)
        return {"conversation": conv, "messages": msgs}
