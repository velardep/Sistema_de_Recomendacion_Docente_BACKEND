# SIPRE — Backend

API REST del Sistema de Recomendación Docente. Construida con FastAPI y Python, usa Supabase como base de datos, Google Gemini como LLM y tres redes neuronales propias (RED1, RED2, RED3) para clasificación y recomendaciones pedagógicas. Los pesos de los modelos se descargan automáticamente desde Cloudflare R2 al iniciar.

---

## Requisitos

- Python 3.10+
- Cuenta en [Supabase](https://supabase.com)
- Clave API de [Google AI Studio](https://aistudio.google.com) (Gemini)
- Cuenta en [Cloudflare R2](https://cloudflare.com) con los pesos de los modelos subidos

---

## Configurar la base de datos

En el SQL Editor de Supabase ejecutar los scripts de `scripts db/` en este orden:

1. `PerfilDocenteyPoliticasRLS.sql`
2. `ChatGeneral.sql`
3. `RecomendacionesYAcciones.sql`
4. `EspaciosTrabajo.sql`
5. `IngestaArchivos.sql`
6. `CerebroSemantico(pgvector).sql`

En **Storage → Buckets** crear dos buckets privados: `pdc-library` y `espacio-files`.

---

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
SUPABASE_URL=https://<tu-proyecto>.supabase.co
SUPABASE_ANON_KEY=<tu-anon-key>

GEMINI_API_KEY=<tu-gemini-api-key>

R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<tu-r2-access-key>
R2_SECRET_ACCESS_KEY=<tu-r2-secret-key>
R2_BUCKET=sistema-docente-sipre-modelos

RED1_R2_PREFIX=models/red1
RED2_R2_PREFIX=models/red2
RED3_R2_PREFIX=models/red3

PDC_LIBRARY_BUCKET=pdc-library
ESPACIO_FILES_BUCKET=espacio-files

PDC_ENABLE_RED1=true
PDC_ENABLE_RAG=true
PDC_ENABLE_RED2=true
```

---

## Instalación y ejecución

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API queda disponible en `http://localhost:8000`.
Documentación interactiva en `http://localhost:8000/docs`.

---

## Ingestar el Prontuario (RAG)

Para que el chat y el generador de PDC puedan buscar contenido curricular:

```bash
python scripts/ingest_prontuario_pdf.py ruta/al/Prontuario.pdf
```

---

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servidor |
| POST | `/auth/register` | Registrar docente |
| POST | `/auth/login` | Iniciar sesión |
| GET/PUT | `/me` | Perfil del docente |
| POST | `/chat` | Chat con IA (RAG + Gemini) |
| GET | `/chats` | Listar conversaciones |
| POST/GET | `/espacios` | Gestionar espacios de trabajo |
| POST | `/pdc/generate` | Generar PDC (.docx) |
| GET | `/red3/recommendations` | Recomendaciones personalizadas |

Todos los endpoints (excepto `/health`, `/auth/register` y `/auth/login`) requieren header `Authorization: Bearer <token>`.
