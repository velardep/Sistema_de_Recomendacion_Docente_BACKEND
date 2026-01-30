# app/application/use_cases/crear_chat_espacio.py
class CrearChatEspacioUseCase:
    def __init__(self, auth_client, espacios_repo, chat_espacios_repo):
        self.auth_client = auth_client
        self.espacios_repo = espacios_repo
        self.chat_espacios_repo = chat_espacios_repo

    async def execute(self, access_token: str, espacio_id: str, titulo: str | None):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return None

        return await self.chat_espacios_repo.crear_conversacion(
            access_token=access_token,
            espacio_id=espacio_id,
            docente_id=docente_id,
            titulo=titulo,
        )
