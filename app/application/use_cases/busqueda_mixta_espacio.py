from typing import Any

class BusquedaMixtaEspacioUseCase:
    def __init__(self, auth_client, embeddings_model, busqueda_rpc, espacios_repo):
        self.auth_client = auth_client
        self.embeddings_model = embeddings_model
        self.busqueda_rpc = busqueda_rpc
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str, espacio_id: str, req: dict[str, Any]):
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        # Valida que el espacio exista (RLS también protege, pero así devolvemos claro)
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return {"docente": [], "global": [], "combinado": []}

        vec = self.embeddings_model.embed(req["texto"])

        # Docente: solo embeddings del espacio (material propio)
        docente_results = await self.busqueda_rpc.buscar(
            access_token=access_token,
            query_vec=vec,
            top_k=req["top_k_docente"],
            tipo_fuente="archivo",
            espacio_id=espacio_id,
            docente_id=docente_id
        )

        # Global: prontuario obligatorio
        global_results = []
        if req["top_k_global"] > 0:
            global_results = await self.busqueda_rpc.buscar(
                access_token=access_token,
                query_vec=vec,
                top_k=req["top_k_global"],
                tipo_fuente="prontuario",
                espacio_id=None,
                docente_id=docente_id
            )

        pond = float(req["ponderacion_docente"])

        def normalize(rows, origen: str, mult: float):
            out = []
            for r in rows:
                sim = float(r.get("similitud") or 0.0)
                out.append({
                    **r,
                    "origen": origen,
                    "score_ponderado": sim * mult,
                })
            return out

        docente_norm = normalize(docente_results, "docente", pond)
        global_norm = normalize(global_results, "prontuario", 1.0)

        combinado = sorted(docente_norm + global_norm, key=lambda x: x["score_ponderado"], reverse=True)

        return {
            "docente": docente_norm,
            "global": global_norm,
            "combinado": combinado
        }
