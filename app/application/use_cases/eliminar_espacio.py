# app/application/use_cases/eliminar_espacio.py

# Use case del flujo de ESPACIOS DE TRABAJO. Se encarga de eliminar un espacio
# existente delegando la operación directamente al repositorio de espacios.
# Actualmente no agrega lógica adicional (validaciones o limpieza asociada),
# por lo que actúa como un simple puente hacia la capa de persistencia.

class EliminarEspacioUseCase:
    def __init__(self, espacios_repo):
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str, espacio_id: str):
        return await self.espacios_repo.eliminar(access_token, espacio_id)
