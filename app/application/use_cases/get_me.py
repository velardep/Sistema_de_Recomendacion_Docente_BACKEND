class GetMeUseCase:
    def __init__(self, auth_client, docente_repo):
        self.auth_client = auth_client
        self.docente_repo = docente_repo

    async def execute(self, access_token: str) -> dict:
        user = await self.auth_client.get_user(access_token)
        user_id = user["id"]
        perfil = await self.docente_repo.get_by_id(access_token, user_id)
        return {"user": user, "perfil": perfil}
