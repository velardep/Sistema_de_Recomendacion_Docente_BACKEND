class BuscarSemanticoUseCase:
    def __init__(self, auth_client, embeddings_model, rpc):
        self.auth_client = auth_client
        self.embeddings_model = embeddings_model
        self.rpc = rpc

    async def execute(self, access_token: str, texto: str, top_k: int,
                      tipo_fuente: str | None, espacio_id: str | None):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        vec = self.embeddings_model.embed(texto)
        return await self.rpc.buscar(
            access_token=access_token,
            query_vec=vec,
            top_k=top_k,
            tipo_fuente=tipo_fuente,
            espacio_id=espacio_id,
            docente_id=docente_id
        )
