class ListarAccionesRecomendacionUseCase:
    def __init__(self, repo):
        self.repo = repo

    async def execute(self, access_token: str, recomendacion_id: str):
        return await self.repo.listar_acciones(access_token, recomendacion_id)
