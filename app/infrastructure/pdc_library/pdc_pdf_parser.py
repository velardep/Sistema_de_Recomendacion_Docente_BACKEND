from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------
# Normalización / limpieza
# ---------------------------------------------------------
_WS_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")

# símbolos frecuentes como viñetas o decoradores de carátulas
_BULLET_PREFIX_RE = re.compile(r"^\s*([✓✔•\-\–\—\*\u2022\u25AA\u25CF\u25A0\u25B6\u27A4\u27A1\u2192\u00BB\u00B7\u25E6]+)\s*")

# “headers” principales que sí nos importan para parsing
_HEADER_MAP = {
    "PRACTICA": "practica",
    "PRÁCTICA": "practica",
    "TEORIA": "teoria",
    "TEORÍA": "teoria",
    "VALORACION": "valoracion",
    "VALORACIÓN": "valoracion",
    "PRODUCCION": "produccion",
    "PRODUCCIÓN": "produccion",
    "PRODUCTO": "producto",
    "PRODUCTOS": "producto",
    "BIBLIOGRAFIA": "bibliografia",
    "BIBLIOGRAFÍA": "bibliografia",
    "CRITERIOS": "criterios",
    "CRITERIOS DE EVALUACION": "criterios",
    "CRITERIOS DE EVALUACIÓN": "criterios",
    "OBJETIVO HOLISTICO": "objetivo",
    "OBJETIVO HOLÍSTICO": "objetivo",
    "PERFIL DE SALIDA": "perfil",
    "CONTENIDOS": "contenidos",
}

# Dimensiones (criterios)
_DIM_WORDS = ["SER", "SABER", "HACER", "DECIDIR"]

# líneas “ruidosas” típicas de PDFs exportados o capas raras
_NOISE_LINE_RE = re.compile(
    r"^\s*(\{'.+|'\w+':|\}\s*$|\],\s*$|'\w+_|\[|\]|\)\s*$)\s*$"
)

# Detecta “artefactos” embebidos dentro de un párrafo (dict/listas con recursos)
_EMBEDDED_ARTIFACT_HINTS = re.compile(
    r"(\{\s*'|\"?\bactividad_practica\b\"?|\"?\blectura_pdf\b\"?|\"?\bpresentacion\b\"?|\"?\bcuestionarios\b\"?|\"?\bvideo\b\"?)",
    re.IGNORECASE,
)

def _strip_embedded_artifacts(paragraph: str) -> str:
    """
    Corta o descarta artefactos embebidos (listas/dicts serializados) dentro de un párrafo,
    para no contaminar TEORIA/PRACTICA/PRODUCCION.
    """
    p = (paragraph or "").strip()
    if not p:
        return ""

    # 0) Si el párrafo ES claramente una lista serializada -> descartar completo
    # Ej: "['Diapositivas ...', '...']" o "[ ... ]"
    if p.startswith("['") or p.startswith('["') or p.startswith("[") or p.startswith("{'") or p.startswith('{"'):
        return ""

    # 1) Corta si aparece un dict literal embebido
    idx = p.find("{'")
    if idx == -1:
        idx = p.find('{"')
    if idx != -1 and idx > 0:
        p = p[:idx].strip()

    # 2) Corta si aparecen hints de keys (cuando vienen)
    m = _EMBEDDED_ARTIFACT_HINTS.search(p)
    if m and m.start() > 40:
        p = p[: m.start()].strip()

    # 3) Corta si aparece un patrón típico de "lista de strings" embebida:
    #    - "', '"  (items separados por comillas)
    #    - "], ["  (listas encadenadas)
    #    - "'], [" o "'], '" (cierres + continuación)
    list_cut_patterns = [
        r"'\s*,\s*'",      # ...', '...
        r'"\s*,\s*"',      # ...", "...
        r"\]\s*,\s*\[",    # ], [
        r"\]\s*,\s*'",     # ], '...
        r"\]\s*,\s*\"",    # ], "...
    ]
    cut_at = None
    for pat in list_cut_patterns:
        mm = re.search(pat, p)
        if mm:
            pos = mm.start()
            if pos > 40:
                cut_at = pos if cut_at is None else min(cut_at, pos)

    if cut_at is not None:
        p = p[:cut_at].strip()

    # 4) Si quedó con mucha “basura de lista”, descartamos
    #    (protege casos como: termina con "], [" o contiene demasiados corchetes)
    if p.count("[") + p.count("]") >= 2:
        # si casi todo son símbolos o quedó muy corto, descartar
        if len(p) < 60:
            return ""
        # si aún así tiene un cierre raro al final, recorta
        p = p.split("]")[0].strip()

    # Limpieza final
    p = p.strip(" ,;:-\n\t\"'")

    return p


def _clean_text(t: str) -> str:
    t = (t or "").replace("\x00", " ")
    t = _WS_RE.sub(" ", t)
    t = _MULTI_NL_RE.sub("\n\n", t)
    return t.strip()


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(data))
        parts: List[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return _clean_text("\n".join(parts))
    except Exception:
        return ""


def _normalize_lines(raw_text: str) -> List[str]:
    """
    - Quita bullets raros al inicio de línea (✓, •, etc.)
    - Filtra líneas basura (restos de dict/listas embebidas)
    - Mantiene headers y dimensiones
    """
    if not raw_text:
        return []

    lines = [ln.strip() for ln in raw_text.split("\n")]
    out: List[str] = []

    for ln in lines:
        if not ln:
            out.append("")  # respetamos saltos
            continue

        # elimina bullets prefix
        ln2 = _BULLET_PREFIX_RE.sub("", ln).strip()

        # si quedó vacío, mantenemos como salto
        if not ln2:
            out.append("")
            continue

        # filtra basura evidente (pero sin matar headers)
        up = ln2.upper().strip(" :.-")
        if up in _HEADER_MAP or up in _DIM_WORDS:
            out.append(ln2)
            continue

        # elimina líneas que parecen residuos de dict/listas embebidas
        if _NOISE_LINE_RE.match(ln2):
            continue

        out.append(ln2)

    # compacta demasiados vacíos seguidos
    compact: List[str] = []
    empties = 0
    for ln in out:
        if ln == "":
            empties += 1
            if empties <= 2:
                compact.append("")
        else:
            empties = 0
            compact.append(ln)
    return compact


def _is_major_header(line: str) -> Optional[str]:
    """
    Detecta si la línea es un header principal.
    Devuelve la key normalizada (ej: "teoria") o None.
    """
    if not line:
        return None

    up = line.upper().strip()
    up = up.strip(" :.-")

    # algunos PDFs ponen "PRODUCTOS:" o "PRODUCTO FINAL:"
    up = up.replace("PRODUCTO FINAL", "PRODUCTO")
    up = up.replace("PRODUCTOS:", "PRODUCTOS")
    up = up.replace("PRODUCTO:", "PRODUCTO")

    # normaliza espacios múltiples
    up = re.sub(r"\s+", " ", up)

    return _HEADER_MAP.get(up)


def _is_dim_header(line: str) -> Optional[str]:
    if not line:
        return None
    up = line.upper().strip(" :.-")
    if up in _DIM_WORDS:
        return up
    return None


def _join_wrapped_paragraphs(lines: List[str]) -> List[str]:
    """
    Convierte líneas cortadas en párrafos:
    - Une líneas si no parecen header/dim y no terminan en puntuación fuerte.
    - Respeta saltos vacíos como “corte de párrafo”.
    """
    paras: List[str] = []
    buf: List[str] = []

    def flush():
        nonlocal buf
        if buf:
            paras.append(" ".join(buf).strip())
            buf = []

    def ends_strong(s: str) -> bool:
        return bool(re.search(r"[.!?;:]$", s.strip()))

    for ln in lines:
        if ln == "":
            flush()
            continue

        # no juntamos headers/dimensiones dentro de párrafos
        if _is_major_header(ln) or _is_dim_header(ln):
            flush()
            paras.append(ln.strip())
            continue

        if not buf:
            buf.append(ln)
            continue

        prev = buf[-1]
        # si el anterior termina fuerte, empezamos nuevo párrafo
        if ends_strong(prev):
            flush()
            buf.append(ln)
        else:
            # unimos (wrap típico de pdf)
            buf.append(ln)

    flush()
    return [p for p in paras if p and len(p.strip()) >= 2]


def parse_pdc_pdf_to_red3_bloques(data: bytes) -> Dict[str, Any]:
    """
    Devuelve el mismo formato que DOCX:
      {
        "teoria": [...],
        "practica": [...],
        "produccion": [...],
        "producto": "...",
        "criterios": {"SER": "...", "SABER": "...", "HACER": "...", "DECIDIR": "..."}
      }

    Mejoras:
    - Soporta bullets/símbolos raros (carátulas)
    - Reconstruye párrafos desde líneas “wrap”
    - Headers robustos
    - Criterios por bloques SER/SABER/HACER/DECIDIR aunque no vengan como "SER:"
    - Filtra residuos tipo "{'lectura_pdf': ...}"
    """
    raw = _extract_pdf_text(data)
    if not raw or len(raw) < 30:
        return {
            "teoria": [],
            "practica": [],
            "produccion": [],
            "producto": "",
            "criterios": {"SER": "", "SABER": "", "HACER": "", "DECIDIR": ""},
        }

    lines = _normalize_lines(raw)
    paras = _join_wrapped_paragraphs(lines)

    # Secciones acumuladas
    sections: Dict[str, List[str]] = {
        "practica": [],
        "teoria": [],
        "valoracion": [],
        "produccion": [],
        "producto": [],
        "criterios": [],
    }

    # Criterios por dimensión
    criterios_dims: Dict[str, List[str]] = {k: [] for k in _DIM_WORDS}

    current_section: Optional[str] = None
    current_dim: Optional[str] = None

    def push_text(target_list: List[str], txt: str):
        t = (txt or "").strip()
        if not t:
            return

        # ✅ Corta artefactos embebidos tipo dict/lista (recursos) dentro del párrafo
        t = _strip_embedded_artifacts(t)
        if not t or len(t) < 20:
            return

        # evita “headers” repetidos como contenido
        if _is_major_header(t) or _is_dim_header(t):
            return

        # evita basura residual (líneas completas raras)
        if _NOISE_LINE_RE.match(t):
            return

        target_list.append(t)

    for p in paras:
        # headers principales
        sec = _is_major_header(p)
        if sec:
            current_section = sec
            current_dim = None
            continue

        # headers de dimensiones dentro de criterios
        dim = _is_dim_header(p)
        if dim:
            current_section = "criterios"
            current_dim = dim
            continue

        # asignación
        if current_section == "criterios" and current_dim:
            push_text(criterios_dims[current_dim], p)
        elif current_section in sections:
            push_text(sections[current_section], p)
        else:
            # fuera de secciones: ignoramos (carátulas, datos referenciales, etc.)
            continue

    # Construye producto:
    # En muchos PDC PDF aparece como "Productos:" y luego una descripción larga.
    producto_txt = ""
    if sections["producto"]:
        # toma el primer bloque “largo”
        # (si hay varios, los une)
        producto_txt = " ".join(sections["producto"]).strip()

    # Criterios: une cada dimensión en un string
    criterios_out = {
        "SER": " ".join(criterios_dims["SER"]).strip(),
        "SABER": " ".join(criterios_dims["SABER"]).strip(),
        "HACER": " ".join(criterios_dims["HACER"]).strip(),
        "DECIDIR": " ".join(criterios_dims["DECIDIR"]).strip(),
    }

    # Teoría / práctica / producción como lista de párrafos (como DOCX)
    return {
        "teoria": sections["teoria"],
        "practica": sections["practica"],
        "produccion": sections["produccion"],
        "producto": producto_txt,
        "criterios": criterios_out,
    }