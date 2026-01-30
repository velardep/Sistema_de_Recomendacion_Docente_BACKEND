class ListarEspaciosUseCase:
    def __init__(self, espacios_repo):
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str):
        return await self.espacios_repo.listar(access_token)
