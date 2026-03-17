# Este use case forma parte del flujo de autenticación y se encarga de iniciar sesión
# a un usuario usando email y contraseña. Su única responsabilidad es recibir esas
# credenciales y delegar la operación al cliente de autenticación.

class AuthLoginUseCase:

    def __init__(self, auth_client):
        self.auth_client = auth_client

    async def execute(self, email: str, password: str) -> dict:
        return await self.auth_client.login_password(email, password)
