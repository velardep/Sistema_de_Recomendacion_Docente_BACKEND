# app/interfaces/api/routes/pdc.py

# Este archivo define la ruta de la API para generación de PDC.
# Permite crear documentos PDC en formato DOCX basados en datos proporcionados.
# Utiliza casos de uso para procesar la solicitud y generar el documento.
# Retorna el archivo generado como una respuesta de streaming.

# Framework - FastAPI
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse

# Interfaces - Dependencias
from app.interfaces.api.dependencies.pdc_deps import get_generate_pdc_uc

# Aplicación - Casos de uso
from app.application.use_cases.generate_pdc import GeneratePdcUseCase

# Creación del router para rutas de PDC con prefijo /pdc y etiqueta pdc.
router = APIRouter(prefix="/pdc", tags=["pdc"])

# Función utilitaria para extraer el token Bearer del header de autorización.
# Valida que el header exista y comience con "Bearer", luego extrae el token.
def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Use: Bearer <token>")
    return authorization.split(" ", 1)[1].strip()

# Endpoint POST para generar un documento PDC.
# Extrae token, ejecuta el caso de uso con los datos y retorna el DOCX como streaming.
@router.post("/generate")
async def generate_pdc(
    req: dict,
    authorization: str | None = Header(default=None, alias="Authorization"),
    uc: GeneratePdcUseCase = Depends(get_generate_pdc_uc),
):
    try:
        # Extrae el token Bearer del header de autorización.
        token = extract_bearer_token(authorization)

        # Ejecuta el caso de uso para generar el PDC con token y datos de solicitud.
        result = await uc.execute(token, req)

        # Retorna el documento DOCX generado como respuesta de streaming.
        return StreamingResponse(
            result["docx"],
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": "attachment; filename=PDC.docx"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))