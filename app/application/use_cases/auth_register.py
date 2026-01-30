class AuthRegisterUseCase:
    def __init__(self, auth_client):
        self.auth_client = auth_client

    async def execute(self, email: str, password: str) -> dict:
        return await self.auth_client.signup(email, password)
