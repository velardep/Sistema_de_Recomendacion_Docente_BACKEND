class CrearRecomendacionUseCase:
    def __init__(self, auth_client, repo):
        self.auth_client = auth_client
        self.repo = repo

    async def execute(self, access_token: str, payload: dict):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        data = {
            "docente_id": docente_id,
            "conversacion_id": payload.get("conversacion_id"),
            "mensaje_id": payload.get("mensaje_id"),
            "tipo": payload["tipo"],
            "modelo": payload.get("modelo", "mock"),
            "contenido": payload["contenido"],
            "metadatos": payload.get("metadatos", {}),
        }
        return await self.repo.crear_recomendacion(access_token, data)
