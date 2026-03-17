# app/application/use_cases/listar_chats_espacio.py

# Use case del flujo de ESPACIOS DE TRABAJO. Recupera la lista de conversaciones
# (chats) asociadas a un espacio específico. Primero valida que el espacio exista
# y sea accesible para el usuario, y luego delega al repositorio de chats del
# espacio la obtención de las conversaciones.

class ListarChatsEspacioUseCase:
    def __init__(self, espacios_repo, chat_espacios_repo):
        self.espacios_repo = espacios_repo
        self.chat_espacios_repo = chat_espacios_repo

    async def execute(self, access_token: str, espacio_id: str):
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return []
        return await self.chat_espacios_repo.listar_conversaciones(access_token, espacio_id)
