# app/application/use_cases/crear_espacio.py

# Este use case pertenece al flujo de ESPACIOS DE TRABAJO y se encarga de crear
# un nuevo espacio asociado al docente autenticado. Primero obtiene al usuario
# desde el access_token, extrae su id y luego arma el payload final combinando
# ese docente_id con los datos enviados desde el frontend para delegar la creación
# al repositorio de espacios.

class CrearEspacioUseCase:
    def __init__(self, auth_client, espacios_repo):
        self.auth_client = auth_client
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str, data: dict):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]
        payload = {"docente_id": docente_id, **data}
        return await self.espacios_repo.crear(access_token, payload)
