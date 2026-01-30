import os, json, httpx
from sentence_transformers import SentenceTransformer

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

assert SUPABASE_URL and SERVICE_KEY, "Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env.local"

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def vlit(vec):
    return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

with open("data/prontuario_min.json", "r", encoding="utf-8") as f:
    temas = json.load(f)

async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        for t in temas:
            # 1) insertar tema
            r = await client.post(f"{SUPABASE_URL}/rest/v1/temas_curriculares", headers=headers, json=t)
            r.raise_for_status()
            tema_row = r.json()[0]
            tema_id = tema_row["id"]

            # 2) embedding del texto combinando campos
            texto = f"{t.get('nivel','')} {t.get('grado','')} {t.get('area','')} | {t['tema']} - {t.get('descripcion','')}"
            vec = model.encode([texto], normalize_embeddings=True)[0].tolist()

            emb_payload = {
                "docente_id": None,
                "espacio_id": None,
                "tipo_fuente": "prontuario",
                "fuente_id": tema_id,
                "texto": texto,
                "embedding": vlit(vec),
                "metadatos": {"nivel": t.get("nivel"), "grado": t.get("grado"), "area": t.get("area")}
            }

            r2 = await client.post(f"{SUPABASE_URL}/rest/v1/embeddings_texto", headers=headers, json=emb_payload)
            r2.raise_for_status()

            print("OK tema:", t["tema"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
