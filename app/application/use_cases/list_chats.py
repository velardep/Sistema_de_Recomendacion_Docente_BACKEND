# app/application/use_cases/list_chats.py

# Use case del flujo de CHAT GENERAL que recupera la lista de conversaciones
# accesibles para el usuario autenticado dentro del módulo de chat general.

class ListChatsUseCase:
    def __init__(self, repo):
        self.repo = repo

    async def execute(self, access_token: str):
        return await self.repo.list_conversations(access_token)
