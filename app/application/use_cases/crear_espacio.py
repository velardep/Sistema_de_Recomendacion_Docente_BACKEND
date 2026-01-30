class CrearEspacioUseCase:
    def __init__(self, auth_client, espacios_repo):
        self.auth_client = auth_client
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str, data: dict):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]
        payload = {"docente_id": docente_id, **data}
        return await self.espacios_repo.crear(access_token, payload)
