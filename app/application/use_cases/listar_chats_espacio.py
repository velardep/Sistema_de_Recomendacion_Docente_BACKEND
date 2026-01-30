# app/application/use_cases/listar_chats_espacio.py
class ListarChatsEspacioUseCase:
    def __init__(self, espacios_repo, chat_espacios_repo):
        self.espacios_repo = espacios_repo
        self.chat_espacios_repo = chat_espacios_repo

    async def execute(self, access_token: str, espacio_id: str):
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return []
        return await self.chat_espacios_repo.listar_conversaciones(access_token, espacio_id)
