# app/application/use_cases/actualizar_espacio.py

# Use case del flujo de ESPACIOS DE TRABAJO encargado de actualizar los datos
# de un espacio existente. Recibe un diccionario con los campos a modificar y
# delega la operación al repositorio. Si el espacio no existe o no es accesible
# bajo las reglas de seguridad, se devuelve un error HTTP 404.
from fastapi import HTTPException

class ActualizarEspacioUseCase:
    def __init__(self, espacios_repo):
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str, espacio_id: str, data: dict):
        # Delegación directa al repositorio de espacios para aplicar la actualización.
        updated = await self.espacios_repo.actualizar(access_token, espacio_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Espacio no encontrado")
        return updated
