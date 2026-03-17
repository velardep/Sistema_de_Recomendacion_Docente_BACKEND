# app/application/use_cases/get_me.py

# Use case del flujo de PERFIL. Se encarga de obtener la información del usuario
# autenticado y su perfil docente dentro del sistema. Primero valida el access_token
# consultando al cliente de autenticación para obtener los datos del usuario, luego
# utiliza el id del usuario para recuperar el perfil docente almacenado en la base
# de datos. Finalmente devuelve ambos datos juntos (usuario + perfil).

class GetMeUseCase:
    def __init__(self, auth_client, docente_repo):
        self.auth_client = auth_client
        self.docente_repo = docente_repo

    async def execute(self, access_token: str) -> dict:
        user = await self.auth_client.get_user(access_token)
        user_id = user["id"]
        perfil = await self.docente_repo.get_by_id(access_token, user_id)
        return {"user": user, "perfil": perfil}
