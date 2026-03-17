# app/application/use_cases/listar_espacios.py

# Use case del flujo de ESPACIOS DE TRABAJO que recupera todos los espacios
# asociados al docente autenticado. La lógica de filtrado por usuario se
# delega al repositorio y a las políticas de seguridad en la base de datos.

class ListarEspaciosUseCase:
    def __init__(self, espacios_repo):
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str):
        # Consulta al repositorio para obtener la lista de espacios accesibles para el usuario.
        return await self.espacios_repo.listar(access_token)
