# app/interfaces/api/routes/pdc_library.py

# Este archivo define las rutas de la API para gestión de la biblioteca PDC.
# Incluye endpoints para listar, subir, eliminar y descargar archivos PDC,
# con integración a RED3 para registro de eventos y actualización de perfiles.
# Maneja autenticación vía tokens Bearer y validaciones de archivos.

from __future__ import annotations

# Librerías estándar
from io import BytesIO

# Framework - FastAPI
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

# Interfaces - Dependencias
from app.interfaces.api.dependencies.pdc_library_deps import get_pdc_library_repo
from app.interfaces.api.dependencies.red3_deps import get_red3_service

# Infraestructura - PDC Library
from app.infrastructure.pdc_library.pdc_library_repo import PdcLibraryRepo, DOCX_MIME, PDF_MIME
from app.infrastructure.pdc_library.pdc_docx_parser import parse_pdc_docx_to_red3_bloques
from app.infrastructure.pdc_library.pdc_pdf_parser import parse_pdc_pdf_to_red3_bloques

# Creación del router para rutas de biblioteca PDC con prefijo /pdc-library y etiqueta pdc-library.
router = APIRouter(prefix="/pdc-library", tags=["pdc-library"])

# Función utilitaria para extraer el token Bearer del header de autorización.
# Valida que el header exista y comience con "Bearer", luego extrae el token.
def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Use: Bearer <token>")
    return authorization.split(" ", 1)[1].strip()

# Función asíncrona para obtener el ID del usuario desde Supabase.
# Realiza una petición GET a la API de Supabase para validar el token y obtener el ID.
async def get_user_id_from_supabase(repo: PdcLibraryRepo, token: str) -> str:
    import httpx

    url = f"{repo.base}/auth/v1/user"
    headers = {"apikey": repo.anon_key, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers)
        if r.status_code >= 400:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        return r.json()["id"]

# Endpoint GET para listar los PDC del usuario.
# Extrae token y ejecuta el método de listado del repositorio.
@router.get("/list")
async def list_my_pdc(
    authorization: str | None = Header(default=None, alias="Authorization"),
    repo: PdcLibraryRepo = Depends(get_pdc_library_repo),
):
    try:
        token = extract_bearer_token(authorization)
        return await repo.list_items(token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint POST para subir un archivo PDC.
# Valida archivo, sube a storage, inserta en BD, parsea con RED3 y registra evento.
@router.post("/upload")
async def upload_pdc(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None, alias="Authorization"),
    repo: PdcLibraryRepo = Depends(get_pdc_library_repo),
    red3=Depends(get_red3_service),
):
    try:
        token = extract_bearer_token(authorization)

        # Determina el tipo de archivo basado en la extensión del nombre.
        name = (file.filename or "").lower()
        is_docx = name.endswith(".docx")
        is_pdf = name.endswith(".pdf")

        # Valida que el archivo sea únicamente .docx o .pdf.
        if not (is_docx or is_pdf):
            raise HTTPException(status_code=400, detail="Solo se permite .docx o .pdf")

        # Obtiene el ID del docente desde Supabase validando el token y lee el contenido.
        docente_id = await get_user_id_from_supabase(repo, token)
        content = await file.read()

        # Verifica que el archivo no esté vacío antes de procesar.
        if not content:
            raise HTTPException(status_code=400, detail="Archivo vacío")

        # Determina el tipo MIME basado en si es PDF o DOCX.
        mime = PDF_MIME if is_pdf else DOCX_MIME

        # Sube el archivo al storage de Supabase y obtiene la ruta de almacenamiento.
        storage_path = await repo.upload_file(
            access_token=token,
            docente_id=docente_id,
            filename=file.filename,
            content=content,
            content_type=mime,
        )

        # Inserta un registro en la base de datos con los metadatos del archivo.
        row = await repo.insert_item(
            access_token=token,
            docente_id=docente_id,
            original_name=file.filename,
            storage_path=storage_path,
            mime_type=mime,
            size_bytes=len(content),
        )

        # Inicializa la estructura de bloques para análisis con RED3.
        bloques = {
            "teoria": [],
            "practica": [],
            "produccion": [],
            "producto": "",
            "criterios": {"SER": "", "SABER": "", "HACER": "", "DECIDIR": ""},
        }

        # Intenta parsear el contenido del archivo para extraer bloques pedagógicos.
        try:
            if is_docx:
                bloques = parse_pdc_docx_to_red3_bloques(content) or bloques
            elif is_pdf:
                bloques = parse_pdc_pdf_to_red3_bloques(content) or bloques
        except Exception:
            # Si el parsing falla, mantiene bloques vacío sin interrumpir el proceso.
            pass

        # Registra el evento de subida en RED3 y actualiza el perfil del docente.
        try:
            await red3.record_event_best_effort(
                token,
                docente_id=docente_id,
                event_type="pdc_library_upload",
                meta={
                    "source": "user_upload",
                    "kind": "pdc",
                    "item_id": row.get("id"),
                    "original_name": row.get("original_name"),
                    "storage_path": row.get("storage_path"),
                    "mime_type": row.get("mime_type"),
                    "size_bytes": row.get("size_bytes"),
                    "bloques": bloques,
                },
            )
            await red3.update_profile_best_effort(token, docente_id=docente_id, window_days=30)
        except Exception:
            # Si falla el registro en RED3, continúa sin afectar el upload.
            pass

        # Retorna el registro insertado como confirmación del upload exitoso.
        return row

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint DELETE para eliminar un PDC.
# Elimina de BD, registra evento en RED3 y borra de storage.
@router.delete("/delete/{item_id}")
async def delete_pdc(
    item_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    repo: PdcLibraryRepo = Depends(get_pdc_library_repo),
    red3=Depends(get_red3_service),
):
    try:
        token = extract_bearer_token(authorization)

        # Obtiene el ID del docente desde Supabase para validar propiedad.
        docente_id = await get_user_id_from_supabase(repo, token)

        # Elimina el registro del item de la base de datos (RLS valida ownership).
        it = await repo.delete_item(token, item_id)  # RLS valida ownership

        # Registra el evento de eliminación en RED3 y actualiza el perfil.
        try:
            await red3.record_event_best_effort(
                token,
                docente_id=docente_id,
                event_type="pdc_library_delete",
                meta={
                    "item_id": it.get("id"),
                    "original_name": it.get("original_name"),
                    "storage_path": it.get("storage_path"),
                },
            )
            await red3.update_profile_best_effort(token, docente_id=docente_id, window_days=30)
        except Exception:
            # Si falla el registro en RED3, continúa con la eliminación.
            pass

        # Intenta borrar el archivo del storage de Supabase (best-effort).
        try:
            await repo.delete_file(token, it["storage_path"])
        except Exception as e:
            # Retorna éxito con advertencia si no se pudo borrar el storage.
            return {"ok": True, "warning": f"No se pudo borrar storage: {str(e)}"}

        # Retorna confirmación de eliminación exitosa.
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint GET para descargar un PDC.
# Obtiene archivo de storage, registra evento en RED3 y retorna como streaming.
@router.get("/download/{item_id}")
async def download_pdc(
    item_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    repo: PdcLibraryRepo = Depends(get_pdc_library_repo),
    red3=Depends(get_red3_service),
):
    try:
        token = extract_bearer_token(authorization)

        # Obtiene el ID del docente desde Supabase para validar acceso.
        docente_id = await get_user_id_from_supabase(repo, token)

        # Recupera los metadatos del item de la base de datos (RLS valida acceso).
        it = await repo.get_item_by_id(token, item_id)  # RLS

        # Descarga el contenido del archivo desde el storage de Supabase.
        data = await repo.download_file(token, it["storage_path"])

        # Registra el evento de descarga en RED3 y actualiza el perfil.
        try:
            await red3.record_event_best_effort(
                token,
                docente_id=docente_id,
                event_type="pdc_library_download",
                meta={
                    "item_id": it.get("id"),
                    "original_name": it.get("original_name"),
                    "storage_path": it.get("storage_path"),
                    "size_bytes": it.get("size_bytes"),
                },
            )
            await red3.update_profile_best_effort(token, docente_id=docente_id, window_days=30)
        except Exception:
            # Si falla el registro en RED3, continúa con la descarga.
            pass

        # Crea un buffer en memoria para el contenido descargado.
        buf = BytesIO(data)
        buf.seek(0)

        # Determina el nombre del archivo para la descarga.
        filename = it.get("original_name") or "PDC.docx"

        # Retorna una respuesta de streaming para descargar el archivo.
        return StreamingResponse(
            buf,
            media_type=it.get("mime_type") or DOCX_MIME,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))