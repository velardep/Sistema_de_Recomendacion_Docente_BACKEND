# scripts/ingest_prontuario_pdf.py
# INGESTA DE PRONTUARIOS Y ARCHIVOS GENERALES PARA NUTRIR AL SISTEMA DE RAG (retrieval-augmented generation) DE SOPORTE DOCENTE
# Este script lee un PDF, lo divide en chunks, genera embeddings y los sube a la tabla embeddings_texto vinculados a un tema_curricular específico (nivel=GLOBAL_PDF, area=PRONTUARIO).
# Luego, el sistema de RAG puede usar estos embeddings para responder preguntas sobre el prontuario
import sys
import os
import argparse
import hashlib
import re
import httpx
import asyncio
import fitz  # PyMuPDF
import torch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.infrastructure.ai.red1_classifier import Red1Classifier
from app.infrastructure.ai.red2_classifier import Red2Classifier

from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv


# =========================
# ENV
# =========================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SERVICE_KEY:
    raise RuntimeError(
        "Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en el .env"
    )

SUPABASE_URL = SUPABASE_URL.rstrip("/")

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

MODEL_NAME = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer(MODEL_NAME)


# =========================
# RUTAS MODELOS (RUTA REAL)
# =========================

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

RED1_EXPORT_DIR = os.path.join(BASE_DIR, "app", "infrastructure", "ai", "red1_model")
RED2_DIR = os.path.join(BASE_DIR, "app", "infrastructure", "ai", "red2_model")

if not os.path.exists(RED1_EXPORT_DIR):
    raise RuntimeError(f"No existe red1_model en: {RED1_EXPORT_DIR}")

if not os.path.exists(RED2_DIR):
    raise RuntimeError(f"No existe red2_model en: {RED2_DIR}")

red1 = Red1Classifier(
    RED1_EXPORT_DIR,
    device="cuda" if torch.cuda.is_available() else "cpu"
)

red2 = Red2Classifier(RED2_DIR)


# =========================
# UTILIDADES
# =========================

def vlit(vec):
    return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def normalize_text(t: str) -> str:
    t = t.replace("\x00", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# =========================
# LECTURA PDF (ROBUSTA)
# =========================

def read_pdf_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)

    total_pages = len(doc)
    print(f"\n📄 Total páginas detectadas: {total_pages}")

    parts = []
    pages_with_text = 0

    for i, page in enumerate(doc):
        txt = page.get_text("text")
        if txt.strip():
            parts.append(txt)
            pages_with_text += 1
        else:
            print(f"⚠️ Página {i+1} sin texto")

    print(f"✅ Páginas con texto extraído: {pages_with_text}")

    full_text = "\n\n".join(parts)

    print(f"🧮 Caracteres totales extraídos: {len(full_text)}")

    print("\n----- INICIO DEL TEXTO -----\n")
    print(full_text[:800])

    print("\n----- FINAL DEL TEXTO -----\n")
    print(full_text[-800:])

    return full_text


# =========================
# CHUNKING
# =========================

def chunk_text(text: str, max_chars: int = 900, overlap: int = 120):
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
        start = end - overlap
        if start < 0:
            start = 0
        if end == n:
            break

    print(f"\n📦 Total chunks generados: {len(chunks)}")
    return chunks


# =========================
# DB OPERATIONS
# =========================

async def ensure_tema_pdf(client, pdf_name, pdf_hash):
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
        print("♻️ Documento ya existía, actualizando metadatos...")
        tema_id = rows[0]["id"]

        await client.patch(
            f"{SUPABASE_URL}/rest/v1/temas_curriculares?id=eq.{tema_id}",
            headers=headers,
            json={
                "metadatos": {
                    "tipo": "pdf_prontuario",
                    "hash": pdf_hash,
                    "archivo": pdf_name,
                }
            },
        )

        return tema_id

    print("🆕 Insertando nuevo documento...")
    r2 = await client.post(
        f"{SUPABASE_URL}/rest/v1/temas_curriculares",
        headers=headers,
        json={
            "nivel": "GLOBAL_PDF",
            "grado": "-",
            "area": "PRONTUARIO",
            "tema": pdf_name,
            "descripcion": "Prontuario global cargado desde PDF",
            "metadatos": {
                "tipo": "pdf_prontuario",
                "hash": pdf_hash,
                "archivo": pdf_name,
            },
        },
    )
    r2.raise_for_status()
    return r2.json()[0]["id"]


async def delete_old_embeddings(client, tema_id):
    print("🗑 Eliminando embeddings anteriores...")
    await client.delete(
        f"{SUPABASE_URL}/rest/v1/embeddings_texto",
        headers=headers,
        params={
            "tipo_fuente": "eq.prontuario",
            "fuente_id": f"eq.{tema_id}",
        },
    )

async def delete_old_prontuario_labels(client, tema_id):
    print("🗑 Eliminando labels Red2 prontuario anteriores...")
    await client.delete(
        f"{SUPABASE_URL}/rest/v1/red2_chunk_labels_prontuario",
        headers=headers,
        params={"fuente_id": f"eq.{tema_id}"},
    )


async def insert_embeddings(client, tema_id, pdf_name, chunks):
    print("🧠 Generando embeddings...")

    texts = [
        f"PRONTUARIO PDF: {pdf_name} | chunk {i+1}/{len(chunks)}\n{c}"
        for i, c in enumerate(chunks)
    ]

    vectors = model.encode(texts, normalize_embeddings=True).tolist()

    payloads = []
    for i, (text, vec) in enumerate(zip(texts, vectors)):
        payloads.append({
            "docente_id": None,
            "espacio_id": None,
            "tipo_fuente": "prontuario",
            "fuente_id": tema_id,
            "texto": text,
            "embedding": vlit(vec),
            "metadatos": {
                "archivo": pdf_name,
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
        })


    inserted_rows = []

    BATCH = 50
    inserted = 0

    for i in range(0, len(payloads), BATCH):
        batch = payloads[i:i+BATCH]
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/embeddings_texto",
            headers=headers,
            json=batch,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            inserted_rows.extend(data)
        inserted += len(batch)
        print(f"   ➜ Insertados {inserted}/{len(payloads)}")

    print(f"\n✅ Total filas insertadas: {inserted}")

    # verificación real en DB
    verify = await client.get(
        f"{SUPABASE_URL}/rest/v1/embeddings_texto",
        headers=headers,
        params={
            "select": "count",
            "tipo_fuente": "eq.prontuario",
            "fuente_id": f"eq.{tema_id}",
        },
    )

    print("🔎 Verificación DB completada.")

    # 🔒 asegurar orden por chunk_index (evita mismatch silencioso)
    inserted_rows.sort(key=lambda r: int((r.get("metadatos") or {}).get("chunk_index", 0)))
    return inserted_rows

async def label_prontuario_with_reds(client, tema_id, pdf_name, chunks, inserted_rows):
    """
    Genera Red1+Red2 para cada chunk y guarda en:
    public.red2_chunk_labels_prontuario
    """
    if not inserted_rows or len(inserted_rows) != len(chunks):
        raise RuntimeError("No coincide cantidad de chunks con filas insertadas en embeddings_texto")

    payloads = []

    for i, (chunk_text, row) in enumerate(zip(chunks, inserted_rows)):
        emb_id = row["id"]

        # ---- Red1
        r1 = red1.classify_text(chunk_text)
        areas_top = r1.get("areas_top")
        dims_probs = r1.get("dims_probs")

        # ---- Red2 (depende de Red1)
        r2 = red2.predict(
            text=chunk_text,
            areas_top=areas_top,
            dims_probs=dims_probs,
            tipo_fuente="archivo",      # ✅ permitido por tu red2
            top_k=5,
            query_for_post=chunk_text
        )

        payloads.append({
            "embedding_texto_id": emb_id,
            "fuente_id": tema_id,
            "tipo_fuente": "archivo",
            "red1_areas_top": areas_top,
            "red1_dims_probs": dims_probs,
            "red2_top": r2.top,
            "red2_probs": r2.probs,
            "metadatos": {
                "real_tipo_fuente": "prontuario",
                "archivo": pdf_name,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
        })

    # insert batch
    BATCH = 100
    inserted = 0
    for i in range(0, len(payloads), BATCH):
        batch = payloads[i:i+BATCH]
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/red2_chunk_labels_prontuario",
            headers=headers,
            json=batch
        )
        r.raise_for_status()
        inserted += len(batch)
        print(f"   🧩 Red2 prontuario labels insertados: {inserted}/{len(payloads)}")

    print("✅ Red2 prontuario labels completados.")

# =========================
# MAIN
# =========================

async def main(pdf_path, max_chars, overlap):
    pdf_name = os.path.basename(pdf_path)

    raw = read_pdf_text(pdf_path)
    text = normalize_text(raw)

    if not text:
        raise SystemExit("❌ No se pudo extraer texto del PDF.")

    pdf_hash = sha1(text)

    chunks = chunk_text(text, max_chars, overlap)

    async with httpx.AsyncClient(timeout=600) as client:
        tema_id = await ensure_tema_pdf(client, pdf_name, pdf_hash)
        await delete_old_embeddings(client, tema_id)
        await delete_old_prontuario_labels(client, tema_id)
        inserted_rows = await insert_embeddings(client, tema_id, pdf_name, chunks)
        await label_prontuario_with_reds(client, tema_id, pdf_name, chunks, inserted_rows)

    print("\n🎯 PROCESO COMPLETADO\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--max_chars", type=int, default=900)
    ap.add_argument("--overlap", type=int, default=120)
    args = ap.parse_args()

    asyncio.run(main(args.pdf, args.max_chars, args.overlap))