# app/application/use_cases/generate_pdc_use_case.py

# Use case del flujo de GENERACION Y ALMACENAMIENTO DE PDC. Se encarga de
# construir un PDC a partir de los datos del docente, combinando señales de
# RED1, contexto recuperado desde prontuario por RAG y guidance de RED2.
# Luego genera el contenido final con el LLM, guarda trazabilidad completa
# en base de datos, renderiza el DOCX y registra el evento en RED3.
from __future__ import annotations

import json
import re
import time

from typing import Any, Dict, List, Optional, Union
from app.infrastructure.pdc.docx_renderer import render_pdc_docx
from app.infrastructure.config.settings import settings

# Regex auxiliar para extraer JSON aunque el LLM lo devuelva envuelto
# en bloques tipo ```json ... ```.
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

# Limpia fences de markdown para dejar solo el contenido útil antes de parsear.
def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    m = _JSON_FENCE_RE.search(t)
    if m:
        return m.group(1).strip()
    return t

# Extrae el primer objeto JSON balanceado encontrado en la salida del LLM,
# incluso si viene mezclado con texto adicional.
def _extract_first_json_object(text: str) -> str:
    t = _strip_code_fences(text)
    start = t.find("{")
    if start == -1:
        return t

    depth = 0
    in_str = False
    esc = False

    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return t[start : i + 1]
    return t

# Intenta parsear la salida del LLM como JSON válido. Si falla, devuelve una
# estructura mínima segura para que el render del DOCX no se rompa.
def _safe_parse_generado(llm_text: str) -> Dict[str, Any]:
    raw = llm_text or ""
    candidate = _extract_first_json_object(raw).strip()

    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # fallback: NO rompe el docx, y evita "json en objetivo"
    return {
        "objetivo_holistico": _strip_code_fences(raw).strip(),
        "practica": [],
        "teoria": [],
        "valoracion": [],
        "produccion": [],
        "recursos": [],
        "criterios": {"SER": [], "SABER": [], "HACER": [], "DECIDIR": []},
        "producto": "",
    }

# Normaliza valores a lista de strings para evitar inconsistencias en bloques
# que luego serán usados por RED3 o por el render del documento.
def _ensure_list(v: Any) -> List[str]:
    """
    Fuerza a lista de strings.
    - si ya es lista -> limpia y devuelve
    - si es string -> lo mete como [string] (sin inventar splits raros)
    - si es None -> []
    - si es otro -> [str(v)]
    """
    if v is None:
        return []
    if isinstance(v, list):
        out: List[str] = []
        for x in v:
            if x is None:
                continue
            s = str(x).strip()
            if s:
                out.append(s)
        return out
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    s = str(v).strip()
    return [s] if s else []

# Fuerza la estructura de criterios a las cuatro dimensiones estándar:
# SER, SABER, HACER y DECIDIR.
def _normalize_criterios(c: Any) -> Dict[str, Union[str, List[str]]]:
    c = c or {}
    if not isinstance(c, dict):
        return {"SER": "", "SABER": "", "HACER": "", "DECIDIR": ""}

    def pick(*keys: str) -> Any:
        for k in keys:
            if k in c:
                return c.get(k)
        return ""

    return {
        "SER": pick("SER", "Ser", "ser"),
        "SABER": pick("SABER", "Saber", "saber"),
        "HACER": pick("HACER", "Hacer", "hacer"),
        "DECIDIR": pick("DECIDIR", "Decidir", "decidir"),
    }

# Normaliza solo los bloques necesarios para registrar el PDC generado como
# evento interpretable dentro de RED3.
def normalize_generado_for_red3(generado: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza SOLO lo necesario para red3/meta:
    - practica/teoria/produccion siempre como arrays
    - criterios con llaves estándar
    """
    g = generado or {}
    return {
        "practica": _ensure_list(g.get("practica")),
        "teoria": _ensure_list(g.get("teoria")),
        "produccion": _ensure_list(g.get("produccion")),
        "criterios": _normalize_criterios(g.get("criterios")),
        "producto": (g.get("producto") or "").strip() if isinstance(g.get("producto"), str) else (g.get("producto") or ""),
    }

# Este use case orquesta el pipeline completo de generación de PDC:
# request -> señales (RED1/RAG/RED2) -> LLM -> persistencia -> DOCX -> RED3.
class GeneratePdcUseCase:

    # Pesos declarativos usados dentro del prompt para indicar la importancia
    # relativa de RED1, RED2 y RAG en la construcción del PDC.
    WEIGHT_RED1 = 0.35
    WEIGHT_RED2 = 0.25
    WEIGHT_RAG = 0.40

    def __init__(
        self,
        auth_client,
        embeddings_model,
        busqueda_rpc,
        red1_service,
        red2_guidance_service,
        pdc_repo,
        llm_client,
        red3_service=None,
    ):
        self.auth_client = auth_client
        self.embeddings_model = embeddings_model
        self.busqueda_rpc = busqueda_rpc
        self.red1_service = red1_service
        self.red2_guidance_service = red2_guidance_service
        self.pdc_repo = pdc_repo
        self.llm_client = llm_client
        self.red3_service = red3_service

        # Flags controladas por variables de entorno (.env).
        # Permiten activar o desactivar partes del pipeline del PDC
        # (RED1, RAG, RED2) sin modificar código ni frontend.
        self.enable_red1 = settings.pdc_enable_red1
        self.enable_rag = settings.pdc_enable_rag
        self.enable_red2 = settings.pdc_enable_red2

    async def execute(self, access_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.time()

        # Primero identifica al docente autenticado y separa las secciones principales
        # del payload que alimentarán el análisis y la generación del PDC.
        user = await self.auth_client.get_user(access_token)
        docente_id = user["id"]

        identificacion = payload.get("identificacion", {}) or {}
        contexto = payload.get("contexto", {}) or {}
        variables = payload.get("variables", {}) or {}
        contenidos: List[str] = variables.get("contenidos", []) or []

        # 1) Crea el request del PDC en base de datos antes de generar contenido para
        # asegurar trazabilidad completa desde el inicio del proceso.
        pdc_request_id = await self.pdc_repo.create_request(access_token, docente_id, payload)

        # 2) Construye un texto base unificado con los datos más importantes del PDC.
        # Este texto sirve como entrada común para RED1 y para la búsqueda RAG.
        texto_analisis = (
            f"[PDC_REQUEST_ID={pdc_request_id}]\n"
            f"AREA: {identificacion.get('area')}\n"
            f"NIVEL: {identificacion.get('nivel')}\n"
            f"ANIO: {identificacion.get('anio_escolaridad')}\n"
            f"PSP: {contexto.get('psp_titulo')}\n"
            f"ACTIVIDAD: {contexto.get('psp_actividad')}\n"
            f"OBJ_PAT: {contexto.get('objetivo_holistico_pat')}\n"
            f"CONTENIDOS: {' | '.join(contenidos)}\n"
        )

        # 3) Si RED1 está habilitada, clasifica el request del PDC para estimar
        # dimensiones pedagógicas y área principal antes de redactar el documento.
        red1_result = None
        dims_probs: Dict[str, Any] = {}
        area_main: Optional[str] = None

        if self.enable_red1:
            red1_result = await self.red1_service.clasificar_y_guardar(
                access_token,
                docente_id=docente_id,
                espacio_id=None,
                conversacion_espacio_id=None,
                mensaje_espacio_id=None,
                tipo_fuente="mensaje",  
                fuente_id=pdc_request_id,  
                chunk_index=None,
                texto=texto_analisis,
            )
            dims_probs = (red1_result or {}).get("dims_probs") or {}
            area_main = (red1_result or {}).get("area_main")

        # 4) Si RAG está habilitado, busca contexto en el prontuario usando embeddings
        # del texto de análisis para recuperar fragmentos temáticamente relevantes.
        rag_results = []
        context_chunks: List[str] = []

        if self.enable_rag:
            # Convierte el texto de análisis en un embedding para consultar similitud
            # semántica contra embeddings del prontuario almacenados en la base de datos.
            vec = self.embeddings_model.embed(texto_analisis)
            rag_results = await self.busqueda_rpc.buscar(
                access_token=access_token,
                query_vec=vec,
                top_k=6,
                tipo_fuente="prontuario",
                espacio_id=None,
                docente_id=docente_id,
            )
            # resultados traen "texto"
            context_chunks = [r.get("texto") for r in (rag_results or []) if r.get("texto")]

        # =========================================================
        # 5) Si RED2 está habilitada y hubo resultados RAG, genera guidance didáctica
        # adicional para orientar mejor la redacción final del PDC.
        # =========================================================
        guidance = None
        if self.enable_red2 and (rag_results or []):
            guidance = await self.red2_guidance_service.build_guidance_from_rag_resultados(
                access_token,
                rag_results or [],
                top_k=5,
            )

        # =========================================================
        # 6) Prompt principal que obliga al LLM a devolver un PDC en formato JSON y a
        # respetar nivel, año, tiempo, contenidos y señales obtenidas del sistema.
        # =========================================================
        prompt = f"""
Eres un experto en planificación educativa boliviana (Ley 070) y debes redactar un PDC técnico, coherente y viable.

REGLAS DE ORO:
- Debes devolver SOLO JSON válido. No incluyas texto antes o después.
- Debe tener EXACTAMENTE estas claves: objetivo_holistico, practica, teoria, valoracion, produccion, recursos, criterios, producto.

ADAPTACIÓN POR NIVEL Y AÑO (CRÍTICO):
- NIVEL Y AÑO: El PDC debe ser pedagógicamente coherente con el nivel '{identificacion.get("nivel")}' y el año '{identificacion.get("anio_escolaridad")}'. 
  * Si es Primaria: Lenguaje sencillo, actividades lúdicas, vivenciales y concretas.
  * Si es Secundaria: Lenguaje técnico/científico, mayor profundidad analítica, investigación y pensamiento crítico avanzado.
- DOSIFICACIÓN Y TIEMPO: Ajusta la carga de actividades al 'Tiempo' ({identificacion.get("tiempo")}). No satures si el tiempo es breve; profundiza si es extenso.
- COBERTURA: Asegúrate de que TODOS los '{contenidos}' sean abordados proporcionalmente.

SEÑALES DEL SISTEMA (influyen con pesos):
- Red1 (peso {self.WEIGHT_RED1}): dims_probs={dims_probs}, area_main={area_main}. Prioriza las dimensiones con mayor probabilidad.
- Red2 (peso {self.WEIGHT_RED2}): guidance={guidance}. Integra estas estrategias y recursos recomendados.
- Prontuario/RAG (peso {self.WEIGHT_RAG}): usa CONTEXTO si existe para precisión temática.

DATOS DEL DOCENTE (INPUT):
Unidad Educativa: {identificacion.get("unidad_educativa")}
Nivel: {identificacion.get("nivel")}
Año: {identificacion.get("anio_escolaridad")}
Trimestre: {identificacion.get("trimestre")}
Tiempo: {identificacion.get("tiempo")} 
Área/Materia: {identificacion.get("area")}
PSP: {contexto.get("psp_titulo")}
Actividad PSP: {contexto.get("psp_actividad")}
Objetivo Holístico PAT: {contexto.get("objetivo_holistico_pat")}
Contenidos: {contenidos}

LÓGICA PEDAGÓGICA OBLIGATORIA:
1. Objetivo Holístico: Un solo párrafo (Ser/Saber/Hacer/Decidir). Debe ser una derivación específica del Objetivo del PAT para estos contenidos.
2. Práctica: Inicio vivencial (experiencia o contacto con la realidad) acorde a la edad.
3. Teoría: Explicación formal de los contenidos. Ajusta el rigor científico al año de escolaridad.
4. Valoración: Reflexión ética que una los contenidos con el PSP y la realidad del estudiante.
5. Producción: Acción transformadora que derive en el Producto final.
6. Criterios: Evaluación de las 4 dimensiones coherentes con el Nivel y el Objetivo.
7. Producto: Tangible, evaluable y realizable en el tiempo {identificacion.get("tiempo")}.

Devuelve SOLO JSON.
"""

        # Genera el contenido final del PDC usando el prompt estructurado y el contexto
        # recuperado por RAG cuando esté disponible.
        llm_text = await self.llm_client.generate(
            prompt=prompt,
            context_chunks=context_chunks,
            history=[],
        )

        # Convierte la salida del LLM a una estructura JSON segura para persistirla y renderizarla.
        generado = _safe_parse_generado(llm_text)

        # 7) Guarda trazabilidad de las señales que influyeron en la generación del PDC:
        # RED1, RED2 y resultados recuperados desde prontuario.
        await self.pdc_repo.create_influences(
            access_token,
            pdc_request_id=pdc_request_id,
            docente_id=docente_id,
            red1={
                "enabled": self.enable_red1,
                "dims_probs": dims_probs,
                "area_main": area_main,
                "raw": (red1_result or {}).get("out") if red1_result else None,
                "saved_row": (red1_result or {}).get("db_row") if red1_result else None,
            },
            red2={
                "enabled": self.enable_red2,
                "guidance": guidance,
            },
            prontuario={
                "enabled": self.enable_rag,
                "top_k": 6,
                "hits": len(rag_results or []),
                "results": rag_results or [],
            },
        )

        # Persiste el contenido generado del PDC como documento asociado al request original.
        pdc_document_id = await self.pdc_repo.create_document(
            access_token,
            pdc_request_id=pdc_request_id,
            docente_id=docente_id,
            titulo=f"PDC - {identificacion.get('area') or 'Sin área'}",
            generado=generado,
        )

        # Registra la ejecución técnica del pipeline con métricas básicas de tiempo,
        # flags activados y cantidad de resultados RAG obtenidos.
        await self.pdc_repo.create_run(
            access_token,
            pdc_document_id=pdc_document_id,
            docente_id=docente_id,
            status="ok",
            meta={
                "ms": int((time.time() - t0) * 1000),
                "pdc_request_id": pdc_request_id,
                "pdc_document_id": pdc_document_id,
                "rag_hits": len(rag_results or []),
                "flags": {
                    "red1": self.enable_red1,
                    "rag": self.enable_rag,
                    "red2": self.enable_red2,
                },
            },
            error=None,
        )

        # 8) Renderiza el PDC generado a formato DOCX usando la plantilla y estructura final.
        docx_buffer = render_pdc_docx(payload, generado)


        # Registra el PDC generado como evento en RED3 y actualiza el perfil del docente
        # para que esta producción también influya en su monitoreo adaptativo.
        if hasattr(self, "red3_service") and self.red3_service:
            try:
                # Normaliza los bloques del PDC antes de enviarlos a RED3 para garantizar una
                # estructura consistente en el evento guardado.
                red3_bloques = normalize_generado_for_red3(generado)

                await self.red3_service.record_event_best_effort(
                    access_token,
                    docente_id=docente_id,
                    event_type="pdc_generated",
                    meta={
                        "source": "system_generated",
                        "kind": "pdc",
                        "pdc_request_id": pdc_request_id,
                        "pdc_document_id": pdc_document_id,
                        "area": identificacion.get("area"),
                        "nivel": identificacion.get("nivel"),
                        "anio": identificacion.get("anio_escolaridad"),
                        "tiempo": identificacion.get("tiempo"),
                        "contenidos": contenidos,
                        "bloques": red3_bloques, 
                    },
                )

                await self.red3_service.update_profile_best_effort(
                    access_token,
                    docente_id=docente_id,
                    window_days=30,
                )
            except Exception:
                pass

        # Devuelve el documento renderizado junto con los ids de trazabilidad y la
        # estructura generada para uso inmediato desde frontend o descarga.
        return {
            "docx": docx_buffer,
            "pdc_request_id": pdc_request_id,
            "pdc_document_id": pdc_document_id,
            "generado": generado,
        }