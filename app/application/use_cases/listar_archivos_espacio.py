# app/application/use_cases/listar_archivos_espacio.py

from __future__ import annotations


class ListarArchivosEspacioUseCase:
    def __init__(self, auth_client, espacios_repo, espacio_archivos_repo):
        self.auth = auth_client
        self.espacios_repo = espacios_repo
        self.espacio_archivos_repo = espacio_archivos_repo

    async def execute(self, access_token: str, espacio_id: str) -> list[dict]:
        user = await self.auth.get_user(access_token)
        docente_id = user["id"]

        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return []

        rows = await self.espacio_archivos_repo.listar_por_espacio(access_token, espacio_id)

        # Refuerzo defensivo por si el usuario no debería ver algo fuera de su contexto.
        return [r for r in rows if r.get("docente_id") == docente_id]