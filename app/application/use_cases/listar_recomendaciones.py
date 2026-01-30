class ListarRecomendacionesUseCase:
    def __init__(self, repo):
        self.repo = repo

    async def execute(self, access_token: str):
        return await self.repo.listar_recomendaciones(access_token)
