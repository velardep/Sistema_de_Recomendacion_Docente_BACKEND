from fastapi import HTTPException

def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    text = text.strip()
    if len(text) <= size:
        return [text]
    chunks = []
    i = 0
    step = max(1, size - overlap)
    while i < len(text):
        chunk = text[i:i+size].strip()
        if chunk:
            chunks.append(chunk)
        i += step
    return chunks

class IngestarTextoEspacioUseCase:
    def __init__(self, auth_client, espacios_repo, textos_repo, embeddings_repo, embeddings_model):
        self.auth_client = auth_client
        self.espacios_repo = espacios_repo
        self.textos_repo = textos_repo
        self.embeddings_repo = embeddings_repo
        self.embeddings_model = embeddings_model

    async def execute(self, access_token: str, espacio_id: str, titulo: str | None, texto: str,
                      tam_chunk: int, overlap: int):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        # Verifica que el espacio existe y es del docente (RLS ya ayuda, pero así damos 404 claro)
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            raise HTTPException(status_code=404, detail="Espacio no encontrado")

        # 1) guarda el texto original
        material = await self.textos_repo.crear(access_token, {
            "docente_id": docente_id,
            "espacio_id": espacio_id,
            "titulo": titulo,
            "texto": texto
        })

        # 2) chunking
        chunks = chunk_text(texto, tam_chunk, overlap)

        # 3) insertar embeddings por chunk
        inserted = 0
        for idx, ch in enumerate(chunks):
            vec = self.embeddings_model.embed(ch)

            payload = {
                "docente_id": docente_id,
                "espacio_id": espacio_id,
                "tipo_fuente": "archivo",
                "fuente_id": material["id"],
                "texto": ch,
                "embedding": "[" + ",".join(f"{x:.6f}" for x in vec) + "]",
                "metadatos": {
                    "titulo": titulo,
                    "chunk_index": idx,
                    "total_chunks": len(chunks)
                }
            }
            await self.embeddings_repo.insertar(access_token, payload)
            inserted += 1

        return {
            "material": material,
            "chunks_creados": len(chunks),
            "embeddings_insertados": inserted
        }
