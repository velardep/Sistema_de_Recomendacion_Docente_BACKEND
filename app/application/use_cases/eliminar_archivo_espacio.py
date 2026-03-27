# app/application/use_cases/eliminar_archivo_espacio.py

from __future__ import annotations


class EliminarArchivoEspacioUseCase:
    def __init__(self, auth_client, espacios_repo, espacio_archivos_repo):
        self.auth = auth_client
        self.espacios_repo = espacios_repo
        self.espacio_archivos_repo = espacio_archivos_repo

    async def execute(self, access_token: str, espacio_id: str, file_id: str) -> dict:
        user = await self.auth.get_user(access_token)
        docente_id = user["id"]

        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return {"ok": False, "detail": "Espacio no encontrado"}

        archivo = await self.espacio_archivos_repo.obtener(access_token, espacio_id, file_id)
        if not archivo:
            return {"ok": False, "detail": "Archivo no encontrado"}

        result = await self.espacio_archivos_repo.eliminar_completo(
            access_token=access_token,
            docente_id=docente_id,
            espacio_id=espacio_id,
            file_id=file_id,
        )

        return result if isinstance(result, dict) else {"ok": False, "detail": "No se pudo eliminar el archivo"}