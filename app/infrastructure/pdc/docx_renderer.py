# app/infrastructure/pdc/docx_renderer.py

# Módulo de infraestructura encargado de construir el documento final del PDC
# en formato DOCX. Aquí se definen helpers de estilo y la función principal
# que toma el payload original y el contenido generado para renderizar el
# documento Word con la estructura formal requerida por el sistema.

from io import BytesIO
from typing import Any, Dict, List, Union

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches


# Helpers de estilo
# Configura los márgenes generales del documento para mantener un formato
# uniforme y más cercano al estilo final esperado del PDC.
def _set_page(doc: Document):
    sec = doc.sections[0]
    sec.top_margin = Inches(0.6)
    sec.bottom_margin = Inches(0.6)
    sec.left_margin = Inches(0.8)
    sec.right_margin = Inches(0.8)

# Helper de formato básico para insertar texto dentro de un párrafo con una
# tipografía y tamaño consistentes en todo el documento.
def _set_run(p, text, bold=False, size=11):
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.name = "Calibri"
    return r

# Aplica color de fondo a una celda de tabla usando manipulación XML, útil
# para resaltar encabezados o secciones importantes.
def _shade_cell(cell, fill_hex: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)

# Aplica bordes visibles a una celda individual para mantener el estilo visual
# de tablas y cajas dentro del documento.
def _set_cell_borders(cell, color="2F75B5", size="12"):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)

    for edge in ("top", "left", "bottom", "right"):
        tag = qn(f"w:{edge}")
        element = tcBorders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            tcBorders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)

# Aplica bordes a toda una tabla, incluyendo bordes internos, para que su
# estructura quede claramente delimitada en el documento final.
def _set_table_borders(table, color="2F75B5", size="12"):
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = tblPr.find(qn("w:tblBorders"))
    if tblBorders is None:
        tblBorders = OxmlElement("w:tblBorders")
        tblPr.append(tblBorders)

    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = tblBorders.find(qn(f"w:{edge}"))
        if el is None:
            el = OxmlElement(f"w:{edge}")
            tblBorders.append(el)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), size)
        el.set(qn("w:color"), color)

# Limpia el contenido inicial de una celda y devuelve su primer párrafo para
# poder reutilizarla con formato controlado.
def _clear_cell(cell):
    cell.text = ""
    return cell.paragraphs[0]

# Normaliza distintos tipos de entrada a una lista de strings para facilitar
# el render uniforme de listas, textos simples o valores sueltos.
def _as_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if "\n" in s:
            return [x.strip("•- \t") for x in s.split("\n") if x.strip()]
        return [s]
    return [str(v).strip()]

# Divide un texto largo en frases más manejables para mejorar la legibilidad
# cuando se renderiza como checklist o lista.
def _split_sentences(s: str) -> List[str]:
    import re

    s = (s or "").strip()
    if not s:
        return []
    if "\n" in s:
        return [x.strip("•- \t") for x in s.split("\n") if x.strip()]

    parts = re.split(r"(?<=[\.\;\:])\s+", s)
    parts = [p.strip() for p in parts if p.strip()]
    return parts if len(parts) > 1 else [s]

# Agrega una lista de elementos dentro de una celda usando un formato visual
# tipo checklist con símbolo de verificación.
def _add_checklist(cell, items: Union[List[str], str]):
    lst = _as_list(items)
    if not lst:
        return
    for it in lst:
        p = cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.add_run("✓ " + it)

# Construye una sección en formato de caja con borde para mostrar bloques como
# objetivo holístico, perfil de salida, contenidos o producto. Puede renderizar
# texto corrido o listas según el tipo de contenido recibido.
def _boxed_section(doc: Document, title: str, body: Union[str, List[str]], bullets: bool = True):
    """
    Caja 1x1 con borde.
    bullets=False -> texto corrido (ideal para Objetivo Holístico)
    bullets=True  -> lista con ✓
    """
    t = doc.add_table(rows=1, cols=1)
    _set_table_borders(t)
    c = t.cell(0, 0)
    _set_cell_borders(c)

    p = _clear_cell(c)
    _set_run(p, f"{title}:", bold=False, size=11)
    p.paragraph_format.space_after = Pt(4)

    # Si el contenido ya viene como lista, se recorre directamente para mostrarlo
    # como texto simple o checklist según el parámetro `bullets`.
    if isinstance(body, list):
        lines = _as_list(body)
        if not lines:
            return
        if not bullets:
            p2 = c.add_paragraph(lines[0])
            p2.paragraph_format.space_after = Pt(2)
            return
        for ln in lines:
            p2 = c.add_paragraph()
            p2.paragraph_format.space_after = Pt(0)
            _set_run(p2, "✓ " + ln, size=11)
        return

    # Si el contenido es texto simple, primero se valida que no esté vacío antes
    # de decidir cómo renderizarlo.
    txt = (body or "").strip()
    if not txt:
        return

    if not bullets:
        p2 = c.add_paragraph(txt)
        p2.paragraph_format.space_after = Pt(2)
        return
    
    # Cuando el contenido es un párrafo largo y se quiere mostrar con viñetas,
    # se divide en frases para que el resultado sea más claro visualmente.
    for ln in _split_sentences(txt):
        p2 = c.add_paragraph()
        p2.paragraph_format.space_after = Pt(0)
        _set_run(p2, "✓ " + ln, size=11)


# Función principal que arma el documento DOCX del PDC. Toma los datos de
# entrada del formulario (`payload`) y el contenido generado por el sistema
# (`generado`), organiza las secciones del documento y devuelve el archivo
# final en memoria listo para descarga o almacenamiento.
def render_pdc_docx(payload: dict, generado: dict) -> BytesIO:
    # Inicializa el documento Word y aplica la configuración base de página.
    doc = Document()
    _set_page(doc)

    # TITULO
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run("PLAN DE DESARROLLO CURRICULAR")
    r.bold = True
    r.font.size = Pt(16)
    r.font.name = "Calibri"

    doc.add_paragraph("")

    # Recupera la sección de identificación del payload para poblar los datos referenciales.
    ident = payload.get("identificacion", {}) or {}

    doc.add_paragraph("")
    titulo = doc.add_paragraph()
    _set_run(titulo, "I.- DATOS REFERENCIALES.-", bold=True, size=12)

    doc.add_paragraph("")

    # Define los campos de identificación que se mostrarán en la primera sección del documento.
    datos = [
        ("Distrito Educativo", ident.get("distrito_educativo", "")),
        ("Núcleo Educativo", ident.get("nucleo_educativo", "")),
        ("Unidad Educativa", ident.get("unidad_educativa", "")),
        ("Area/Materia", ident.get("area", "")),
        ("Nivel", ident.get("nivel", "")),
        ("Año de Escolaridad", ident.get("anio_escolaridad", "")),
        ("Docente", ident.get("docente", "")),
        ("Trimestre", ident.get("trimestre", "")),
        ("Tiempo", ident.get("tiempo", "")),
    ]

    # Usa una tabla simple de dos columnas para alinear etiquetas y valores de forma ordenada.
    tabla = doc.add_table(rows=len(datos), cols=2)

    # Recorre cada dato referencial y lo inserta en su fila correspondiente.
    for i, (label, value) in enumerate(datos):
        row = tabla.rows[i].cells

        p0 = row[0].paragraphs[0]
        p0.paragraph_format.space_after = Pt(2)
        _set_run(p0, f"{label}:", bold=False, size=11)

        p1 = row[1].paragraphs[0]
        p1.paragraph_format.space_after = Pt(2)
        _set_run(p1, str(value or ""), size=11)

    # Elimina los bordes de esta tabla para que los datos referenciales queden
    # visualmente más limpios que las tablas metodológicas del PDC.
    tbl = tabla._tbl
    tblPr = tbl.tblPr
    tblBorders = tblPr.find(qn("w:tblBorders"))
    if tblBorders is not None:
        tblPr.remove(tblBorders)

    doc.add_paragraph("")

    # OBJETIVO / PERFIL / CONTENIDOS
    # Renderiza el objetivo holístico como bloque destacado en una caja de texto.
    objetivo = (generado or {}).get("objetivo_holistico", "") or ""
    _boxed_section(doc, "Objetivo Holístico", objetivo, bullets=False)

    # Recupera el perfil de salida generado; si no existe, intenta construir un
    # fallback simple usando criterios disponibles para no dejar la sección vacía.
    perfil = (generado or {}).get("perfil_salida")
    if not perfil:
        crit = (generado or {}).get("criterios", {}) or {}
        perfil = []
        if isinstance(crit, dict):
            for kk in ("SER", "SABER"):
                vv = crit.get(kk) or crit.get(kk.capitalize()) or crit.get(kk.lower())
                if vv:
                    perfil += _as_list(vv)[:1]
    _boxed_section(doc, "Perfil de salida", perfil, bullets=True)

    # Muestra los contenidos del PDC en una caja separada usando formato checklist.
    contenidos = (payload.get("variables", {}) or {}).get("contenidos", []) or []
    _boxed_section(doc, "Contenidos", contenidos, bullets=True)

    doc.add_paragraph("")

    # Construye la tabla principal del documento, donde se organizan orientaciones,
    # materiales y criterios de evaluación.
    main = doc.add_table(rows=2, cols=3)
    _set_table_borders(main)

    # Define y formatea los encabezados de las tres columnas principales.
    headers = main.rows[0].cells
    for i, txt in enumerate(
        ["ORIENTACIONES METODOLÓGICAS", "MATERIALES\nEDUCATIVOS", "CRITERIOS DE\nEVALUACIÓN"]
    ):
        p = _clear_cell(headers[i])
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_run(p, txt, bold=True, size=11)
        _shade_cell(headers[i], "D9E1F2")
        _set_cell_borders(headers[i])

    # Prepara las celdas del cuerpo de la tabla aplicando bordes individuales.
    body = main.rows[1].cells
    for c in body:
        _set_cell_borders(c)

    # Renderiza en la primera columna los cuatro bloques metodológicos del PDC:
    # práctica, teoría, valoración y producción.
    col0 = body[0]
    _clear_cell(col0)

    for label_key, human in [
        ("practica", "PRÁCTICA"),
        ("teoria", "TEORÍA"),
        ("valoracion", "VALORACIÓN"),
        ("produccion", "PRODUCCIÓN"),
    ]:
        ph = col0.add_paragraph()
        _set_run(ph, human, bold=True, size=11)
        items = (generado or {}).get(label_key, [])
        _add_checklist(col0, items)
        col0.add_paragraph("")  # separador

    # Muestra los recursos o materiales y criterios educativos propuestos dentro del documento.
    col1 = body[1]
    _clear_cell(col1)
    recursos = (generado or {}).get("recursos", [])
    _add_checklist(col1, recursos)

    col2 = body[2]
    _clear_cell(col2)
    criterios = (generado or {}).get("criterios", {}) or {}

    # Helper local para recuperar criterios por dimensión aceptando distintas
    # variantes de nombres de clave dentro del JSON generado.
    def _pick_crit(key: str) -> List[str]:
        if not isinstance(criterios, dict):
            return []
        v = criterios.get(key) or criterios.get(key.capitalize()) or criterios.get(key.lower())
        if v is None:
            return []
        if isinstance(v, list):
            return _as_list(v)
        if isinstance(v, str):
            return _split_sentences(v)
        return [str(v)]

    # Renderiza los criterios de evaluación agrupados por las cuatro dimensiones pedagógicas.
    for kk in ["SER", "SABER", "HACER", "DECIDIR"]:
        ph = col2.add_paragraph()
        _set_run(ph, kk, bold=True, size=11)
        _add_checklist(col2, _pick_crit(kk))
        col2.add_paragraph("")

    # PRODUCTO + BIBLIO + FIRMA
    # Si existe producto final, lo muestra en una sección independiente con borde.
    doc.add_paragraph("")
    prod = (generado or {}).get("producto", "")
    if prod:
        _boxed_section(doc, "Productos", prod, bullets=True)

    # Agrega la sección de bibliografía al final del documento.
    doc.add_paragraph("")
    b = doc.add_paragraph()
    _set_run(b, "Bibliografía", bold=True, size=12)

    # Inserta una bibliografía base genérica como apoyo documental del PDC.
    for it in [
        "Planes y Programas del Ministerio de Educación.",
        "Texto de aprendizajes del Ministerio.",
        "Fuentes comunitarias pertinentes.",
    ]:
        p = doc.add_paragraph("✓ " + it)
        p.paragraph_format.space_after = Pt(0)

    # Agrega un espacio de firma con el nombre del docente al final del documento.
    doc.add_paragraph("")
    firma = doc.add_paragraph()
    firma.add_run("______________________________\n")
    firma.add_run(str(ident.get("docente", "") or ""))

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer