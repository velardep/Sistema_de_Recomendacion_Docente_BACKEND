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
