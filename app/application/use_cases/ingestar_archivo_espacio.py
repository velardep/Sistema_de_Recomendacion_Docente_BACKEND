from __future__ import annotations
from fastapi import UploadFile
from typing import List, Dict
import re
import hashlib
import uuid


class IngestarArchivoEspacioUseCase:
    """
    - Valida docente logueado
    - Valida que el espacio exista (RLS)
    - Extrae texto de PDF (por ahora)
    - Chunking
    - Embeddings
    - Inserta en embeddings_texto con espacio_id y tipo_fuente="espacio_archivo"
    """

    def __init__(self, auth_client, espacios_repo, embeddings_model, embeddings_repo):
        self.auth = auth_client
        self.espacios_repo = espacios_repo
        self.embeddings_model = embeddings_model
        self.embeddings_repo = embeddings_repo

    async def execute(self, access_token: str, espacio_id: str, file: UploadFile) -> dict:
        user = await self.auth.get_user(access_token)
        docente_id = user["id"]

        # 1) validar espacio (RLS)
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return {"ok": False, "detail": "Espacio no encontrado"}

        filename = (file.filename or "archivo").strip()
        content_type = (file.content_type or "").lower()

        # 2) leer bytes
        data = await file.read()
        if not data or len(data) < 10:
            return {"ok": False, "detail": "Archivo vacío o inválido"}

        # 3) extraer texto (PDF por ahora)
        text = ""
        if "pdf" in content_type or filename.lower().endswith(".pdf"):
            text = self._extract_text_pdf_bytes(data)
        else:
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = ""

        text = self._clean_text(text)
        if not text or len(text) < 20:
            return {"ok": False, "detail": "No se pudo extraer texto del archivo"}

        # 4) chunking
        chunks = self._chunk_text(text, max_chars=900, overlap=120)
        if not chunks:
            return {"ok": False, "detail": "No se generaron chunks"}

        # 5) generar UUID para fuente_id
        file_id = str(uuid.uuid4())  # ✅ UUID válido para Postgres
        file_hash = hashlib.sha1(data).hexdigest()  # solo para referencia

        # 6) insertar embeddings
        inserted = 0
        for idx, chunk in enumerate(chunks):
            vec = self.embeddings_model.embed(chunk)  # vector de embeddings

            payload = {
                "docente_id": docente_id,
                "espacio_id": espacio_id,
                "tipo_fuente": "archivo",
                "fuente_id": file_id,  # ✅ UUID válido
                "texto": chunk,
                "embedding": vec,
                "metadatos": {
                    "ambito": "espacio",
                    "espacio_id": espacio_id,
                    "archivo": filename,
                    "fuente_id": file_id,    # repetir UUID en metadatos
                    "file_hash": file_hash,  # referencia hash
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "content_type": content_type,
                    "espacio_nombre": espacio.get("nombre"),
                },
            }

            await self.embeddings_repo.insert_embedding(access_token, payload)
            inserted += 1

        return {
            "ok": True,
            "espacio_id": espacio_id,
            "docente_id": docente_id,
            "archivo": filename,
            "file_id": file_id,
            "chunks_insertados": inserted,
        }

    def _clean_text(self, t: str) -> str:
        t = t.replace("\x00", " ")
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        return t.strip()

    def _chunk_text(self, t: str, max_chars: int = 900, overlap: int = 120) -> List[str]:
        paras = [p.strip() for p in t.split("\n") if p.strip()]
        chunks: List[str] = []
        buf = ""

        def flush():
            nonlocal buf
            if buf.strip():
                chunks.append(buf.strip())
            buf = ""

        for p in paras:
            if len(buf) + len(p) + 1 <= max_chars:
                buf = (buf + "\n" + p).strip() if buf else p
            else:
                flush()
                if len(p) <= max_chars:
                    buf = p
                else:
                    start = 0
                    while start < len(p):
                        end = min(start + max_chars, len(p))
                        chunks.append(p[start:end].strip())
                        start = max(0, end - overlap)

        flush()

        if overlap > 0 and len(chunks) > 1:
            out = []
            for i, c in enumerate(chunks):
                if i == 0:
                    out.append(c)
                else:
                    prev = chunks[i - 1]
                    tail = prev[-overlap:] if len(prev) > overlap else prev
                    out.append((tail + "\n" + c).strip())
            chunks = out

        chunks = [c for c in chunks if len(c) >= 30]
        return chunks

    def _extract_text_pdf_bytes(self, data: bytes) -> str:
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(data))
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except Exception:
            return ""
