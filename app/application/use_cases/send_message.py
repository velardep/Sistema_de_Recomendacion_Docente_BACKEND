class SendMessageUseCase:
    def __init__(self, auth_client, repo):
        self.auth_client = auth_client
        self.repo = repo

    async def execute(self, access_token: str, conversation_id: str, content: str):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        # 1) guarda mensaje del usuario
        user_msg = await self.repo.insert_message(
            access_token, conversation_id, docente_id, "user", content, meta={}
        )

        # 2) respuesta "mock" del assistant (luego se reemplaza por IA)
        assistant_text = (
            "Entendido. (Respuesta mock del Slice 2)\n"
            "En el siguiente slice conectaremos IA/RAG, pero tu historial ya queda guardado."
        )

        assistant_msg = await self.repo.insert_message(
            access_token, conversation_id, docente_id, "assistant", assistant_text,
            meta={"mode": "mock"}
        )

        return {"user_message": user_msg, "assistant_message": assistant_msg}
