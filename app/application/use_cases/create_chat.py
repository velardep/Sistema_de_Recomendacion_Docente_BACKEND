# app/application/use_cases/create_chat.py

# Use case del flujo de CHAT GENERAL. Se encarga de crear una nueva conversación
# para el docente autenticado. Primero obtiene el usuario desde el access_token
# y luego delega al repositorio la creación del chat con el título recibido.

class CreateChatUseCase:
    def __init__(self, auth_client, repo):
        self.auth_client = auth_client
        self.repo = repo

    async def execute(self, access_token: str, titulo: str | None):
        user = await self.auth_client.get_user(access_token)
        return await self.repo.create_conversation(access_token, user["id"], titulo)
