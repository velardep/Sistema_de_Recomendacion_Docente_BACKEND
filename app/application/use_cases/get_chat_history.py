# app/application/use_cases/get_chat_history.py

# Use case del flujo de CHAT GENERAL encargado de recuperar una conversación
# existente junto con todos sus mensajes. Primero valida que el chat exista y
# luego consulta su historial completo en el repositorio.

class GetChatHistoryUseCase:
    def __init__(self, repo):
        self.repo = repo

    async def execute(self, access_token: str, conversation_id: str):
        conv = await self.repo.get_conversation(access_token, conversation_id)
        if not conv:
            return None
        msgs = await self.repo.list_messages(access_token, conversation_id)
        return {"conversation": conv, "messages": msgs}
