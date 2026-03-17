# app/infrastructure/pdc_library/pdc_docx_parser.py
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Tuple
import re

from docx import Document


# =========================
# Normalización
# =========================
def _norm(s: str) -> str:
    s = (s or "").replace("\u00a0", " ")
    # NO destruye símbolos (✓, etc). Solo colapsa espacios.
    return re.sub(r"\s+", " ", s).strip()


_BULLET_RE = re.compile(r"^\s*(?:✓|•|\-|\*|\d+[\.\)]|[a-zA-Z][\.\)])\s+")


def _split_to_list(text: str) -> List[str]:
    """
    Convierte texto a lista sin inventar splits raros:
    - Si hay viñetas/numeración -> lista por líneas
    - Si no -> un solo párrafo
    """
    t = (text or "").strip()
    if not t:
        return []

    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if len(lines) <= 1:
        return [_norm(t)]

    bullet_like = sum(1 for ln in lines if _BULLET_RE.match(ln))
    if bullet_like >= max(1, len(lines) // 4):
        out: List[str] = []
        for ln in lines:
            ln2 = _BULLET_RE.sub("", ln).strip()
            if ln2:
                out.append(_norm(ln2))
        return out if out else [_norm(t)]

    return [_norm(t)]


# =========================
# Extracción docx: párrafos + celdas
# =========================
def _iter_doc_blocks(doc: Document) -> List[Tuple[str, str]]:
    """
    Devuelve lista de bloques:
      ('p', 'texto') para paragraphs
      ('cell', 'texto\\ntexto') para celdas de tablas
    """
    out: List[Tuple[str, str]] = []

    for p in doc.paragraphs:
        tx = _norm(p.text)
        if tx:
            out.append(("p", tx))

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                cell_texts = []
                for p in cell.paragraphs:
                    tx = _norm(p.text)
                    if tx:
                        cell_texts.append(tx)
                if cell_texts:
                    out.append(("cell", "\n".join(cell_texts)))

    return out


# =========================
# Parser ministerial robusto
# =========================
# OJO: aquí NO hacemos match de "teoría" suelta, sino de marcadores "TEORÍA ✓"
_SEC_RE = re.compile(
    r"(?i)\b(PRÁCTICA|PRACTICA|TEORÍA|TEORIA|VALORACIÓN|VALORACION|PRODUCCIÓN|PRODUCCION)\b\s*(?:✓|:|-)\s*"
)

_DIM_RE = re.compile(r"(?i)\b(SER|SABER|HACER|DECIDIR)\b\s*(?:✓|:|-)\s*")


def _split_orientaciones(text: str) -> Dict[str, str]:
    """
    Corta una celda tipo:
      "PRÁCTICA ✓ ... TEORÍA ✓ ... VALORACIÓN ✓ ... PRODUCCIÓN ✓ ..."
    usando marcadores fuertes (palabra + ✓/:/-).
    """
    txt = text or ""
    ms = list(_SEC_RE.finditer(txt))
    if not ms:
        return {}

    parts: Dict[str, str] = {}
    for i, m in enumerate(ms):
        key = m.group(1).upper()
        start = m.end()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(txt)
        seg = txt[start:end].strip()
        if seg:
            parts[key] = seg
    return parts


def _split_criterios(text: str) -> Dict[str, str]:
    """
    Corta texto tipo:
      "SER ✓ ... SABER ✓ ... HACER ✓ ... DECIDIR ✓ ..."
    """
    out = {"SER": "", "SABER": "", "HACER": "", "DECIDIR": ""}
    t = text or ""
    ms = list(_DIM_RE.finditer(t))
    if not ms:
        return out

    for i, m in enumerate(ms):
        dim = m.group(1).upper()
        start = m.end()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(t)
        seg = t[start:end].strip()
        seg = re.sub(r"^\s*✓\s*", "", seg).strip()
        out[dim] = _norm(seg)
    return out


def parse_pdc_docx_to_red3_bloques(docx_bytes: bytes) -> Dict[str, Any]:
    """
    Best-effort pero ENFOCADO al formato ministerial común:
    - ORIENTACIONES METODOLÓGICAS suele venir en 1 celda con PRACTICA/TEORIA/VALORACION/PRODUCCION
    - CRITERIOS DE EVALUACIÓN suele venir en otra celda con SER/SABER/HACER/DECIDIR
    - Productos: suele venir en otra celda "Productos:"
    """
    empty = {
        "teoria": [],
        "practica": [],
        "produccion": [],
        "producto": "",
        "criterios": {"SER": "", "SABER": "", "HACER": "", "DECIDIR": ""},
    }

    try:
        doc = Document(BytesIO(docx_bytes))
    except Exception:
        return empty

    blocks = _iter_doc_blocks(doc)

    orient_cell = ""
    criterios_cell = ""
    producto_cell = ""

    for typ, tx in blocks:
        l = tx.lower()

        # 1) Orientaciones: buscamos una celda con >=3 marcadores fuertes (PRACTICA/TEORIA/...)
        if len(_SEC_RE.findall(tx)) >= 3:
            orient_cell = tx

        # 2) Producto(s) en celda "Productos:"
        if l.startswith("productos:") or l.startswith("producto:"):
            producto_cell = tx

        # 3) Criterios: celda con varias dims + ✓
        if "✓" in tx and len(re.findall(r"(?i)\b(SER|SABER|HACER|DECIDIR)\b", tx)) >= 3:
            criterios_cell = tx

    parts = _split_orientaciones(orient_cell)

    # Nota: keys pueden venir con acento o sin acento
    practica_txt = parts.get("PRÁCTICA") or parts.get("PRACTICA") or ""
    teoria_txt = parts.get("TEORÍA") or parts.get("TEORIA") or ""
    produccion_txt = parts.get("PRODUCCIÓN") or parts.get("PRODUCCION") or ""

    practica = _split_to_list(practica_txt)
    teoria = _split_to_list(teoria_txt)
    produccion = _split_to_list(produccion_txt)

    producto = producto_cell
    if producto:
        producto = re.sub(r"(?i)^\s*productos?\s*:\s*", "", producto).strip()
        producto = re.sub(r"^\s*✓\s*", "", producto).strip()
        producto = _norm(producto)

    criterios = _split_criterios(criterios_cell)

    return {
        "teoria": teoria,
        "practica": practica,
        "produccion": produccion,
        "producto": producto,
        "criterios": criterios,
    }