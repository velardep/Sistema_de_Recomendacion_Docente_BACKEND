from fastapi import HTTPException

class ActualizarEspacioUseCase:
    def __init__(self, espacios_repo):
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str, espacio_id: str, data: dict):
        updated = await self.espacios_repo.actualizar(access_token, espacio_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Espacio no encontrado")
        return updated
