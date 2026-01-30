



# scripts/ingest_prontuario_pdf.py
import os
import argparse
import hashlib
import re
import httpx

from sentence_transformers import SentenceTransformer

# PDF reader
from pypdf import PdfReader  # pip install pypdf

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

assert SUPABASE_URL and SERVICE_KEY, "Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

MODEL_NAME = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer(MODEL_NAME)

def vlit(vec):
    # pgvector textual format
    return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"

def read_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    parts = []
    for i, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        if txt.strip():
            parts.append(txt)
    return "\n\n".join(parts)

def normalize_text(t: str) -> str:
    t = t.replace("\x00", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def chunk_text(text: str, max_chars: int = 900, overlap: int = 120):
    """
    Chunking simple por caracteres con solapamiento.
    Para PDFs pequeños funciona bien. Luego lo refinamos si quieres (tokens).
    """
    if max_chars <= overlap:
        raise ValueError("max_chars debe ser > overlap")

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + max_chars, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap  # solapamiento
        if start < 0:
            start = 0
        if end == n:
            break
    return chunks

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

async def ensure_tema_pdf(client: httpx.AsyncClient, pdf_name: str, pdf_hash: str):
    """
    Creamos 1 row en temas_curriculares representando el PDF.
    Para encontrarlo, lo buscamos por metadatos.hash y tema==pdf_name.
    Si no existe, lo insertamos.
    """
    # buscar si ya existe tema con ese hash
    # (filtrar por metadatos->>hash no es directo por PostgREST; usamos metadatos como JSON exacto no es buen filtro)
    # Entonces hacemos estrategia simple:
    # - buscamos por tema == pdf_name y nivel == 'GLOBAL_PDF'
    r = await client.get(
        f"{SUPABASE_URL}/rest/v1/temas_curriculares",
        headers=headers,
        params={
            "select": "*",
            "tema": f"eq.{pdf_name}",
            "nivel": "eq.GLOBAL_PDF",
            "grado": "eq.-",
            "area": "eq.PRONTUARIO",
        },
    )
    r.raise_for_status()
    rows = r.json()

    if rows:
        tema_row = rows[0]
        # actualizamos metadatos con hash por si cambió
        patch_payload = {
            "metadatos": {"tipo": "pdf_prontuario", "hash": pdf_hash, "archivo": pdf_name}
        }
        rp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/temas_curriculares?id=eq.{tema_row['id']}",
            headers=headers,
            json=patch_payload,
        )
        rp.raise_for_status()
        return tema_row["id"]

    # insertar
    payload = {
        "nivel": "GLOBAL_PDF",
        "grado": "-",
        "area": "PRONTUARIO",
        "tema": pdf_name,
        "descripcion": "Prontuario global cargado desde PDF",
        "metadatos": {"tipo": "pdf_prontuario", "hash": pdf_hash, "archivo": pdf_name},
    }
    r2 = await client.post(f"{SUPABASE_URL}/rest/v1/temas_curriculares", headers=headers, json=payload)
    r2.raise_for_status()
    return r2.json()[0]["id"]

async def delete_old_embeddings_for_tema(client: httpx.AsyncClient, tema_id: str):
    # Borra embeddings anteriores de ese documento
    # OJO: requiere Service Role (ya lo usas)
    r = await client.delete(
        f"{SUPABASE_URL}/rest/v1/embeddings_texto",
        headers=headers,
        params={
            "tipo_fuente": "eq.prontuario",
            "fuente_id": f"eq.{tema_id}",
        },
    )
    # PostgREST puede devolver 204 sin body; igual es OK
    if r.status_code not in (200, 204):
        r.raise_for_status()

async def insert_chunks_embeddings(client: httpx.AsyncClient, tema_id: str, pdf_name: str, chunks: list[str]):
    texts_for_embed = []
    payloads = []

    total = len(chunks)
    for i, chunk in enumerate(chunks):
        # texto indexable: puedes incluir cabecera para mejorar recall
        texto_index = f"PRONTUARIO PDF: {pdf_name} | chunk {i+1}/{total}\n{chunk}"
        texts_for_embed.append(texto_index)

    # embeddings en batch (mucho más rápido)
    vecs = model.encode(texts_for_embed, normalize_embeddings=True).tolist()

    for i, (texto_index, vec) in enumerate(zip(texts_for_embed, vecs)):
        payloads.append(
            {
                "docente_id": None,
                "espacio_id": None,
                "tipo_fuente": "prontuario",
                "fuente_id": tema_id,
                "texto": texto_index,
                "embedding": vlit(vec),
                "metadatos": {
                    "archivo": pdf_name,
                    "chunk_index": i,
                    "total_chunks": total,
                },
            }
        )

    # Insertar en lotes
    BATCH = 50
    for i in range(0, len(payloads), BATCH):
        batch = payloads[i : i + BATCH]
        r = await client.post(f"{SUPABASE_URL}/rest/v1/embeddings_texto", headers=headers, json=batch)
        if r.status_code >= 400:
            print("STATUS:", r.status_code)
            print("BODY:", r.text[:2000])  # para no imprimir infinit
        r.raise_for_status()

async def main(pdf_path: str, max_chars: int, overlap: int):
    pdf_name = os.path.basename(pdf_path)
    raw = read_pdf_text(pdf_path)
    text = normalize_text(raw)

    if not text:
        raise SystemExit("PDF sin texto extraíble (escaneado). En ese caso necesitas OCR.")

    pdf_hash = sha1(text)

    chunks = chunk_text(text, max_chars=max_chars, overlap=overlap)

    async with httpx.AsyncClient(timeout=120) as client:
        tema_id = await ensure_tema_pdf(client, pdf_name, pdf_hash)

        # idempotencia: borramos lo anterior de ese tema_id
        await delete_old_embeddings_for_tema(client, tema_id)

        await insert_chunks_embeddings(client, tema_id, pdf_name, chunks)

        print(f"OK. PDF={pdf_name} tema_id={tema_id} chunks={len(chunks)} modelo={MODEL_NAME}")

if __name__ == "__main__":
    import asyncio

    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="Ruta del PDF prontuario")
    ap.add_argument("--max_chars", type=int, default=900)
    ap.add_argument("--overlap", type=int, default=120)
    args = ap.parse_args()

    asyncio.run(main(args.pdf, args.max_chars, args.overlap))
