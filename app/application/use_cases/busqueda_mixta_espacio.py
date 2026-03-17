# app/application/use_cases/busqueda_mixta_espacio.py

# Este use case pertenece al flujo de EMBEDDINGS dentro de ESPACIOS DE TRABAJO.
# Se encarga de ejecutar una búsqueda semántica mixta tomando como base una consulta
# del usuario, generando su embedding y consultando dos fuentes: el material propio
# del espacio y el prontuario global. Luego normaliza ambos resultados, aplica una
# ponderación a los del espacio docente y devuelve también una lista combinada
# ordenada por relevancia.

from typing import Any

class BusquedaMixtaEspacioUseCase:
    def __init__(self, auth_client, embeddings_model, busqueda_rpc, espacios_repo):
        self.auth_client = auth_client
        self.embeddings_model = embeddings_model
        self.busqueda_rpc = busqueda_rpc
        self.espacios_repo = espacios_repo

    async def execute(self, access_token: str, espacio_id: str, req: dict[str, Any]):
        # Primero se identifica al docente autenticado y se valida que el espacio exista
        # y sea accesible.
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]
        espacio = await self.espacios_repo.obtener(access_token, espacio_id)
        if not espacio:
            return {"docente": [], "global": [], "combinado": []}

        # La consulta textual se transforma en un embedding para poder compararla
        # semánticamente contra los embeddings ya almacenados en la base de datos.
        vec = self.embeddings_model.embed(req["texto"])

        # Se consulta primero el material propio del espacio, es decir, contenido cargado
        # por el docente dentro de ese contexto específico de trabajo.
        docente_results = await self.busqueda_rpc.buscar(
            access_token=access_token,
            query_vec=vec,
            top_k=req["top_k_docente"],
            tipo_fuente="archivo",
            espacio_id=espacio_id,
            docente_id=docente_id
        )

        # Luego se consulta el prontuario global como segunda fuente de apoyo, separado
        # del material del espacio para poder combinar ambos resultados después.
        global_results = []
        if req["top_k_global"] > 0:
            global_results = await self.busqueda_rpc.buscar(
                access_token=access_token,
                query_vec=vec,
                top_k=req["top_k_global"],
                tipo_fuente="prontuario",
                espacio_id=None,
                docente_id=None   # PRONTUARIO ES GLOBAL (docente_id en embeddings es NULL)
            )

        # Este valor llega desde el request, el cual es
        # definido en el schema de entrada `BusquedaMixtaRequest` (schemas/busqueda_mixta.py).
        # Define cuánto peso extra tendrán los resultados del espacio del docente frente
        # a los del prontuario global al combinar los rankings.
        # Si vale 1.0, ambos compiten con su similitud original.
        # Si vale más de 1.0, se favorece el material del espacio.
        # El valor por defecto actualmente es 1.25.
        pond = float(req["ponderacion_docente"])

       
        # Esta función toma los resultados crudos devueltos por la búsqueda semántica y
        # les agrega dos campos nuevos:
        # - origen: indica de qué fuente viene cada resultado ("docente" o "prontuario")
        # - score_ponderado: valor final usado para mezclar y ordenar resultados
        #
        # La fórmula aplicada es:
        #     score_ponderado = similitud * mult
        #
        # Donde:
        # - similitud: viene directamente desde la búsqueda vectorial RPC y representa
        #   qué tan parecido es el embedding del resultado respecto a la consulta.
        # - mult: es un factor de ponderación definido por el request o por el propio
        #   flujo del use case para dar más o menos peso a una fuente.
        #
        # En este caso:
        # - los resultados del espacio/docente usan mult = ponderacion_docente
        # - los resultados del prontuario usan mult = 1.0
        #
        # Esto permite favorecer el material propio del espacio sin cambiar la similitud
        # original calculada por la búsqueda semántica.
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

        # Aquí se aplica la ponderación a cada fuente:
        # - docente_norm usa el factor configurado en req["ponderacion_docente"]
        # - global_norm usa 1.0, o sea, mantiene su score base sin ajuste
        #
        # Con esto los resultados del espacio pueden subir o bajar de prioridad
        # respecto a los del prontuario al momento de mezclarlos.
        docente_norm = normalize(docente_results, "docente", pond)
        global_norm = normalize(global_results, "prontuario", 1.0)

        # Finalmente ambas listas se unen y se ordenan de mayor a menor usando el
        # score_ponderado, no la similitud original. Esa es la regla final que decide
        # qué resultados aparecen primero en la respuesta combinada.
        combinado = sorted(docente_norm + global_norm, key=lambda x: x["score_ponderado"], reverse=True)

        return {
            "docente": docente_norm,
            "global": global_norm,
            "combinado": combinado
        }
    

# Ejemplo:
# si un resultado docente tiene similitud 0.80 y ponderacion_docente = 1.2,
# su score_ponderado será 0.96
#
# si un resultado global tiene similitud 0.90 y mult = 1.0,
# su score_ponderado seguirá siendo 0.90
#
# En ese caso, el resultado docente quedará por encima en la lista combinada.
