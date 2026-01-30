from typing import Protocol

class DocenteRepository(Protocol):
    async def get_by_id(self, access_token: str, user_id: str) -> dict | None:
        ...

    async def upsert(self, access_token: str, docente: dict) -> dict:
        ...
