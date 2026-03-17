# app/application/use_cases/upsert_me.py

# Use case del flujo de PERFIL. Se encarga de crear o actualizar el perfil docente
# del usuario autenticado. Primero obtiene el usuario a partir del access_token,
# luego construye el objeto docente combinando los datos enviados desde el frontend
# con la información básica del usuario autenticado. Finalmente delega al repositorio
# docente la operación de upsert (crear si no existe o actualizar si ya existe).

class UpsertMeUseCase:
    def __init__(self, auth_client, docente_repo):
        self.auth_client = auth_client
        self.docente_repo = docente_repo

    async def execute(self, access_token: str, payload: dict) -> dict:
        user = await self.auth_client.get_user(access_token)
        user_id = user["id"]

        docente = {
            "id": user_id,
            "nombres": payload["nombres"],
            "apellidos": payload["apellidos"],
            "email": user.get("email"),
            "unidad_educativa": payload.get("unidad_educativa"),
            "nivel": payload.get("nivel"),
            "grado": payload.get("grado"),
            "ciudad": payload.get("ciudad"),
            "departamento": payload.get("departamento"),
            "preferencias": payload.get("preferencias", {}),
        }
        return await self.docente_repo.upsert(access_token, docente)
