from fastapi import HTTPException

class ObtenerEspacioUseCase:
    def __init__(self, espacios_repo):
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str, espacio_id: str):
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            raise HTTPException(status_code=404, detail="Espacio no encontrado")
        return espacio
