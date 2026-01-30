class GetChatHistoryUseCase:
    def __init__(self, repo):
        self.repo = repo

    async def execute(self, access_token: str, conversation_id: str):
        conv = await self.repo.get_conversation(access_token, conversation_id)
        if not conv:
            return None
        msgs = await self.repo.list_messages(access_token, conversation_id)
        return {"conversation": conv, "messages": msgs}
