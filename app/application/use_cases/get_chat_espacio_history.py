# app/application/use_cases/get_chat_espacio_history.py

# Este use case pertenece al flujo de ESPACIOS DE TRABAJO y se encarga de recuperar
# una conversación de espacio junto con su historial de mensajes. Antes de devolver
# los datos, valida que la conversación exista y que realmente pertenezca al espacio
# solicitado para evitar cruces incorrectos entre conversaciones.

class GetChatEspacioHistoryUseCase:
    def __init__(self, chat_espacios_repo):
        self.chat_espacios_repo = chat_espacios_repo

    async def execute(self, access_token: str, espacio_id: str, conversacion_espacio_id: str):
        conv = await self.chat_espacios_repo.obtener_conversacion(access_token, conversacion_espacio_id)
        if not conv:
            return None

        if str(conv.get("espacio_id")) != str(espacio_id):
            return None

        msgs = await self.chat_espacios_repo.listar_mensajes(access_token, conversacion_espacio_id)
        return {"conversation": conv, "messages": msgs}
