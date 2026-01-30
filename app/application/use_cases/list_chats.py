class ListChatsUseCase:
    def __init__(self, repo):
        self.repo = repo

    async def execute(self, access_token: str):
        return await self.repo.list_conversations(access_token)
