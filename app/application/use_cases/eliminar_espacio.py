class EliminarEspacioUseCase:
    def __init__(self, espacios_repo):
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str, espacio_id: str):
        return await self.espacios_repo.eliminar(access_token, espacio_id)
