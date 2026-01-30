class RegistrarAccionDocenteUseCase:
    def __init__(self, auth_client, repo):
        self.auth_client = auth_client
        self.repo = repo

    async def execute(self, access_token: str, recomendacion_id: str, payload: dict):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        data = {
            "docente_id": docente_id,
            "recomendacion_id": recomendacion_id,
            "accion": payload["accion"],
            "valor": payload.get("valor"),
            "comentario": payload.get("comentario"),
            "metadatos": payload.get("metadatos", {}),
        }
        return await self.repo.crear_accion(access_token, data)
