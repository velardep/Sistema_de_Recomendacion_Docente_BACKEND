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

def _is_truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "si", "sí", "yes", "on"}
    return bool(v)

def _validate_pdc_payload(
    identificacion: Dict[str, Any],
    contexto: Dict[str, Any],
    variables: Dict[str, Any],
    contenidos: List[str],
    use_psp: bool,
) -> None:
    if not str(identificacion.get("area", "") or "").strip():
        raise ValueError("Falta el área")
    if not str(identificacion.get("nivel", "") or "").strip():
        raise ValueError("Falta el nivel")
    if not str(identificacion.get("anio_escolaridad", "") or "").strip():
        raise ValueError("Falta el año de escolaridad")

    # Tiempo ahora debe venir estructurado para acercarse al formato real.
    if not str(identificacion.get("semanas", "") or "").strip():
        raise ValueError("Falta la cantidad de semanas")
    if not str(identificacion.get("periodos_por_semana", "") or "").strip():
        raise ValueError("Falta la cantidad de periodos por semana")

    if not contenidos:
        raise ValueError("Debes ingresar al menos un contenido")

    if use_psp:
        if not str(contexto.get("psp_titulo", "") or "").strip():
            raise ValueError("Falta el título del PSP")
        if not str(contexto.get("psp_actividad", "") or "").strip():
            raise ValueError("Falta la actividad del PSP")
        if not str(contexto.get("objetivo_holistico_pat", "") or "").strip():
            raise ValueError("Falta el Objetivo Holístico PAT")
    else:
        if not str(contexto.get("objetivo_aprendizaje", "") or "").strip():
            raise ValueError("Falta el objetivo de aprendizaje")
        if not str(contexto.get("producto", "") or "").strip():
            raise ValueError("Falta el producto o evidencia esperada")


def _build_texto_analisis(
    identificacion: Dict[str, Any],
    contexto: Dict[str, Any],
    contenidos: List[str],
    use_psp: bool,
) -> str:
    base = [
        f"AREA: {identificacion.get('area', '')}",
        f"NIVEL: {identificacion.get('nivel', '')}",
        f"ANIO: {identificacion.get('anio_escolaridad', '')}",
    ]

    if use_psp:
        base.extend([
            f"PSP: {contexto.get('psp_titulo', '')}",
            f"ACTIVIDAD: {contexto.get('psp_actividad', '')}",
            f"OBJ_PAT: {contexto.get('objetivo_holistico_pat', '')}",
        ])
    else:
        base.extend([
            f"OBJ_APRENDIZAJE: {contexto.get('objetivo_aprendizaje', '')}",
            f"PRODUCTO: {contexto.get('producto', '')}",
            f"METODOLOGIA: {contexto.get('metodologia', '')}",
            f"TIPO_EVALUACION: {contexto.get('tipo_evaluacion', '')}",
        ])

    base.append("CONTENIDOS: " + " | ".join(contenidos))
    return "\n".join(base)


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _build_periodos_label(identificacion: Dict[str, Any]) -> str:
    semanas = _to_int(identificacion.get("semanas"), 0)
    periodos_por_semana = _to_int(identificacion.get("periodos_por_semana"), 0)
    duracion_periodo = str(identificacion.get("duracion_periodo", "") or "").strip()

    total = semanas * periodos_por_semana if semanas > 0 and periodos_por_semana > 0 else 0

    if total > 0 and duracion_periodo:
        return f"{total} periodos ({periodos_por_semana} por semana, {duracion_periodo} min c/u)"
    if total > 0:
        return f"{total} periodos"
    return str(identificacion.get("tiempo", "") or "").strip()


def _build_contenidos_bloque(contenidos: List[str]) -> str:
    return "\n".join(f"- {c}" for c in contenidos if str(c).strip())


def _build_redes_influence_text(
    area_main: str,
    dims_probs: Dict[str, Any],
    guidance: Any,
    context_chunks: List[str],
) -> str:
    return f"""
INFLUENCIA DE REDES Y CONTEXTO:
- RED1 (clasificación pedagógica): orienta el tono, profundidad, tipo de actividades y énfasis del PDC.
- RED1 área principal detectada: {area_main}
- RED1 probabilidades/dimensiones: {json.dumps(dims_probs, ensure_ascii=False)}

- RAG (prontuario recuperado): aporta contexto docente previo y continuidad pedagógica.
- Fragmentos RAG recuperados: {len(context_chunks or [])}

- RED2 (guidance didáctica): sugiere estrategias, enfoque y tipo de recursos/producción.
- Guidance RED2: {json.dumps(guidance, ensure_ascii=False)}
""".strip()

def _build_llm_prompt(
    identificacion: Dict[str, Any],
    contexto: Dict[str, Any],
    contenidos: List[str],
    guidance: Any,
    area_main: str,
    dims_probs: Dict[str, Any],
    use_psp: bool,
    context_chunks: List[str],
) -> str:
    semanas = _to_int(identificacion.get("semanas"), 0)
    periodos_por_semana = _to_int(identificacion.get("periodos_por_semana"), 0)
    duracion_periodo = str(identificacion.get("duracion_periodo", "") or "").strip()
    periodos_label = _build_periodos_label(identificacion)
    contenidos_txt = _build_contenidos_bloque(contenidos)
    redes_txt = _build_redes_influence_text(area_main, dims_probs, guidance, context_chunks)

    base_common = f"""
Eres un experto boliviano en planificación educativa y debes generar un PDC REALISTA, BREVE, DOCENTE y ESTRUCTURADO para SECUNDARIA.

REGLAS GENERALES OBLIGATORIAS:
1. Devuelve SOLO JSON válido.
2. Mantén EXACTAMENTE estas claves:
   objetivo_holistico, practica, teoria, valoracion, produccion, recursos, criterios, producto
3. La redacción NO debe parecer texto literario de IA. Debe sentirse como planificación docente real.
4. Los momentos del proceso formativo deben ser CONCISOS, OPERATIVOS y REALISTAS.
5. Los contenidos deben respetar el tiempo real de planificación:
   - semanas: {semanas}
   - periodos por semana: {periodos_por_semana}
   - duración de cada periodo: {duracion_periodo}
   - total: {periodos_label}

# REGLAS CRÍTICAS PARA MOMENTOS (MUY IMPORTANTE)
6. práctica, teoría, valoración y producción deben ser TEXTOS CORTOS.
7. NO usar semanas dentro de práctica, teoría, valoración o producción.
8. NO usar listas por semana.
9. NO usar markdown (NO **, NO -, NO bullets).
10. Cada momento debe escribirse como UNA SOLA LÍNEA compacta.
11. Separar acciones usando punto y coma (;).
12. Máximo 3 a 4 acciones por cada momento.
13. Evitar explicaciones largas o redundantes.
14. Debe parecer texto real de planificación docente, no una secuencia detallada paso a paso.

# FORMATO ESPERADO DE MOMENTOS (OBLIGATORIO)
Ejemplo correcto:
Práctica: diálogo inicial sobre el tema; identificación de conceptos clave en el entorno; análisis de ejemplos concretos.

Ejemplo incorrecto:
- Semana 1:
- Actividad 1
- Actividad 2

15. Cada bloque debe poder leerse en una sola mirada (como en plantillas reales).
16. La influencia de RED1, RAG y RED2 debe reflejarse en:
   - tipo de actividades
   - nivel de profundidad
   - tipo de producción
   - criterios de evaluación

17. Los contenidos deben mantenerse como están (no inventar estructura nueva si ya vienen organizados).

# RECURSOS DIDÁCTICOS (MEJORA)
18. Los recursos deben ser concretos, útiles y didácticos, no genéricos.
19. Evitar listas vagas como "materiales de escritorio".
20. Incluir entre 3 y 6 recursos máximo.
21. Diferenciar según contexto:

- Si el enfoque es sociocomunitario (PSP):
  usar recursos accesibles: papelógrafos, láminas, material reciclado, textos físicos, recursos del entorno, etc.

- Si el enfoque es académico (sin PSP o institucional):
  se pueden incluir recursos tecnológicos: proyector, computadora, presentaciones digitales, internet, videos educativos, etc.

22. Los recursos deben estar alineados con las actividades y producción.

DATOS:
- Área: {identificacion.get("area")}
- Nivel: {identificacion.get("nivel")}
- Año: {identificacion.get("anio_escolaridad")}
- Trimestre: {identificacion.get("trimestre")}
- Semanas: {semanas}
- Periodos por semana: {periodos_por_semana}
- Duración de periodo: {duracion_periodo}
- Total de periodos: {periodos_label}

CONTENIDOS:
{contenidos_txt}

{redes_txt}

FORMATO DE SALIDA:
{{
  "objetivo_holistico": "texto breve y técnico",
  "practica": ["línea compacta con punto y coma"],
  "teoria": ["línea compacta con punto y coma"],
  "valoracion": ["línea compacta con punto y coma"],
  "produccion": ["línea compacta con punto y coma"],
  "recursos": ["...", "..."],
  "criterios": {{
    "SER": "...",
    "SABER": "...",
    "HACER": "...",
    "DECIDIR": "..."
  }},
  "producto": "texto breve"
}}
""".strip()

    if use_psp:
        return f"""
{base_common}

MODO: CON PSP

DATOS DEL CONTEXTO:
- PSP: {contexto.get("psp_titulo")}
- Actividad PSP: {contexto.get("psp_actividad")}
- Objetivo Holístico PAT: {contexto.get("objetivo_holistico_pat")}

INSTRUCCIONES ESPECÍFICAS:
1. El objetivo_holistico debe articular PSP + PAT + contenidos.
2. La diferencia con el modo sin PSP debe ser visible:
   - lenguaje más sociocomunitario
   - producción más colectiva o contextual
   - valoración conectada con comunidad, identidad, convivencia o realidad local
3. La producción debe sentirse vinculada a una actividad sociocomunitaria o aplicación contextual.
4. RED1 debe influir en el énfasis pedagógico del área y de los criterios.
5. RED2 debe influir en estrategias y recursos.
6. RAG debe influir si aporta continuidad docente o enfoque previo.
7. Mantén formato docente real, breve y operativo.
""".strip()

    return f"""
{base_common}

MODO: SIN PSP

DATOS DEL CONTEXTO:
- Objetivo de aprendizaje: {contexto.get("objetivo_aprendizaje")}
- Producto esperado: {contexto.get("producto")}
- Metodología sugerida: {contexto.get("metodologia")}
- Tipo de evaluación: {contexto.get("tipo_evaluacion")}

INSTRUCCIONES ESPECÍFICAS:
1. NO menciones PSP, PAT ni articulación socioproductiva.
2. La diferencia con el modo con PSP debe ser visible:
   - lenguaje más académico
   - producción más analítica, individual o técnica
   - valoración centrada en aprendizaje, reflexión, responsabilidad y aplicación del conocimiento
3. El objetivo_holistico debe construirse desde el objetivo de aprendizaje y los contenidos.
4. RED1 debe influir en el nivel de profundidad y en el tipo de criterios.
5. RED2 debe influir en metodología, recursos y producción.
6. RAG debe influir solo si aporta continuidad útil.
7. Mantén formato docente real, breve y operativo.
""".strip()




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


        use_psp = _is_truthy(contexto.get("use_psp", True))

        _validate_pdc_payload(
            identificacion=identificacion,
            contexto=contexto,
            variables=variables,
            contenidos=contenidos,
            use_psp=use_psp,
        )

        # 1) Crea el request del PDC en base de datos antes de generar contenido para
        # asegurar trazabilidad completa desde el inicio del proceso.
        pdc_request_id = await self.pdc_repo.create_request(access_token, docente_id, payload)

        # 2) Construye un texto base unificado con los datos más importantes del PDC.
        # Este texto sirve como entrada común para RED1 y para la búsqueda RAG.
        #texto_analisis = (
         #   f"[PDC_REQUEST_ID={pdc_request_id}]\n"
          #  f"AREA: {identificacion.get('area')}\n"
           # f"NIVEL: {identificacion.get('nivel')}\n"
           # f"ANIO: {identificacion.get('anio_escolaridad')}\n"
           # f"PSP: {contexto.get('psp_titulo')}\n"
           # f"ACTIVIDAD: {contexto.get('psp_actividad')}\n"
           # f"OBJ_PAT: {contexto.get('objetivo_holistico_pat')}\n"
           # f"CONTENIDOS: {' | '.join(contenidos)}\n"
        #)

        texto_analisis = _build_texto_analisis(
            identificacion=identificacion,
            contexto=contexto,
            contenidos=contenidos,
            use_psp=use_psp,
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
        prompt = _build_llm_prompt(
            identificacion=identificacion,
            contexto=contexto,
            contenidos=contenidos,
            guidance=guidance,
            area_main=area_main,
            dims_probs=dims_probs,
            use_psp=use_psp,
            context_chunks=context_chunks,
        )

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
                "role_in_generation": "define énfasis pedagógico, profundidad, tono y criterios",
                "dims_probs": dims_probs,
                "area_main": area_main,
                "raw": (red1_result or {}).get("out") if red1_result else None,
                "saved_row": (red1_result or {}).get("db_row") if red1_result else None,
            },
            red2={
                "enabled": self.enable_red2,
                "role_in_generation": "sugiere estrategias, recursos, enfoque metodológico y tipo de producción",
                "guidance": guidance,
            },
            prontuario={
                "enabled": self.enable_rag,
                "role_in_generation": "aporta continuidad docente y contexto recuperado por RAG",
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
                "use_psp": use_psp,
                "input_mode": "with_psp" if use_psp else "without_psp",
                "periodos_label": _build_periodos_label(identificacion),
                "red1_area_main": area_main,
                "red1_dims_probs": dims_probs,
                "red2_guidance_used": bool(guidance),
                "rag_context_hits": len(context_chunks or []),
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
                        "use_psp": use_psp,
                        "objetivo_aprendizaje": contexto.get("objetivo_aprendizaje") if not use_psp else "",
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