# Este use case forma parte del flujo de autenticación y se encarga de registrar
# nuevos usuarios con email y contraseña. La creación real de la cuenta se delega
# al cliente de autenticación conectado con Supabase Auth.

class AuthRegisterUseCase:
    def __init__(self, auth_client):
        self.auth_client = auth_client

    async def execute(self, email: str, password: str) -> dict:
        return await self.auth_client.signup(email, password)
