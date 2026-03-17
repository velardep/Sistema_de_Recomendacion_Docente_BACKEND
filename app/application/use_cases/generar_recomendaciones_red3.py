# app/application/use_cases/generar_recomendaciones_red3.py

# Use case del flujo de RED3 y SUGERENCIAS EN BASE AL PERFIL. Se encarga de
# obtener el perfil adaptativo del docente y sus snapshots recientes, revisar
# si ya existen recomendaciones válidas en caché y, si no existen o son inválidas,
# generar nuevas recomendaciones personalizadas con el LLM a partir de métricas
# reales de los últimos 7 y 30 días.

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

import json
import re

# Regex auxiliar para detectar y extraer JSON cuando el LLM responde envuelto
# en bloques tipo ```json ... ```.
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

# Limpia fences de markdown para dejar solo el contenido útil antes de intentar
# parsear la respuesta del LLM como JSON.
def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    m = _JSON_FENCE_RE.search(t)
    if m:
        return m.group(1).strip()
    return t

# Extrae el primer objeto JSON completo encontrado dentro del texto devuelto
# por el LLM, incluso si viene mezclado con texto adicional.
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

# Intenta convertir la salida del LLM en un diccionario JSON válido; si falla,
# devuelve una estructura vacía compatible con el frontend.
def _safe_parse_json(llm_text: str) -> Dict[str, Any]:
    raw = llm_text or ""
    candidate = _extract_first_json_object(raw).strip()
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {"cards": [], "recomendaciones": []}

# Garantiza que la estructura recibida sea una lista de diccionarios antes
# de normalizar cards y recomendaciones.
def _ensure_recs_list(v: Any) -> List[Dict[str, Any]]:
    if not isinstance(v, list):
        return []
    out: List[Dict[str, Any]] = []
    for x in v:
        if isinstance(x, dict):
            out.append(x)
    return out

# Normaliza cada card o recomendación para asegurar un contrato estable hacia
# el frontend, incluso si el LLM devuelve campos incompletos o inconsistentes.
def _normalize_item(x: Dict[str, Any], fallback_id: str) -> Dict[str, Any]:
    _id = str(x.get("id") or fallback_id)
    titulo = str(x.get("titulo") or "").strip()
    descripcion = str(x.get("descripcion") or "").strip()
    tipo = str(x.get("tipo") or "sugerencia").strip()
    features_used = x.get("features_used")

    if not isinstance(features_used, list):
        features_used = []

    if not titulo:
        titulo = "Sugerencia"
    if not descripcion:
        descripcion = "Recomendación generada por el sistema."

    return {
        "id": _id,
        "titulo": titulo,
        "descripcion": descripcion,
        "tipo": tipo,
        "features_used": features_used
    }

# Devuelve el perfil RED3 del docente, snapshots recientes y un
# conjunto de cards/recomendaciones generadas por LLM. Antes de regenerar,
# revisa una caché persistente en base de datos con validez de 3 días para
# evitar llamadas innecesarias al modelo.
class GenerarRecomendacionesRed3UseCase:

    def __init__(self, auth_client, red3_service, llm_client, llm_recs_repo):
        self.auth = auth_client
        self.red3 = red3_service
        self.llm = llm_client
        self.cache = llm_recs_repo

    async def execute(
        self,
        access_token: str,
        *,
        window_days: int = 30,
        force: bool = False,
    ) -> Dict[str, Any]:
        # Primero identifica al docente autenticado y recupera su perfil RED3 junto con
        # los snapshots recientes que sirven como base real para generar sugerencias.
        user = await self.auth.get_user(access_token)
        docente_id = user["id"]

        # Perfil + snapshots reales (7 y 30 días). El perfil puede ser None si no se ha 
        # calculado aún, pero los snapshots deberían existir aunque vengan vacíos (sin features).
        prof = await self.red3.repo.get_style_profile(access_token, docente_id)
        snap7 = await self.red3.repo.get_latest_snapshot(access_token, docente_id, window_days=7)
        snap30 = await self.red3.repo.get_latest_snapshot(access_token, docente_id, window_days=30)

        # Define la fecha de referencia del análisis. Si existe snapshot de 30 días se
        # usa su period_end; si no, se toma la fecha actual como fallback.
        period_end = None
        if isinstance(snap30, dict) and snap30.get("period_end"):
            period_end = str(snap30["period_end"])
        if not period_end:
            period_end = datetime.now(timezone.utc).date().isoformat()

        # Antes de llamar al LLM se intenta reutilizar una versión reciente guardada en
        # caché. Esto reduce costo, latencia y evita regenerar recomendaciones iguales.
        if not force:
            cached = await self.cache.get_latest_valid(access_token, docente_id, int(window_days))
            if isinstance(cached, dict) and isinstance(cached.get("payload"), dict):
                payload = cached["payload"]

                cards_raw = payload.get("cards") or []
                recs_raw = payload.get("recomendaciones") or []

                # Normalizar SIEMPRE (así se garantiza features_used aunque venga raro)
                cards_norm = [_normalize_item(x if isinstance(x, dict) else {}, f"c-{i+1}") for i, x in enumerate(cards_raw[:6])]
                recs_norm  = [_normalize_item(x if isinstance(x, dict) else {}, f"r-{i+1}") for i, x in enumerate(recs_raw[:8])]

                # Si el cache viejo NO trae features_used, lo consideramos inválido y regeneramos
                cache_has_features = any(len((c.get("features_used") or [])) > 0 for c in cards_norm) or any(
                    len((r.get("features_used") or [])) > 0 for r in recs_norm
                )

                if cache_has_features:
                    return {
                        "profile": prof,
                        "snapshot_7d": snap7,
                        "snapshot_30d": snap30,
                        "cards": cards_norm,
                        "recomendaciones": recs_norm,
                        "meta": {
                            "cached": True,
                            "generated_at": cached.get("generated_at"),
                            "expires_at": cached.get("expires_at"),
                            "period_end": period_end,
                            "window_days": int(window_days),
                        },
                    }
                
        # Extrae las señales reales del perfil y snapshots para construir el prompt
        # con datos medibles, no con textos inventados desde frontend.
        features_7d = (snap7 or {}).get("features") if isinstance(snap7, dict) else None
        features_30d = (snap30 or {}).get("features") if isinstance(snap30, dict) else None
        style_main = (prof or {}).get("style_main") if isinstance(prof, dict) else None
        style_probs = (prof or {}).get("style_probs") if isinstance(prof, dict) else None
        confidence = (prof or {}).get("confidence") if isinstance(prof, dict) else None
        events_count = (prof or {}).get("events_count") if isinstance(prof, dict) else None
        data_strength = (prof or {}).get("data_strength") if isinstance(prof, dict) else None

        # Prompt estructurado para obligar al LLM a devolver únicamente JSON con cards
        # y recomendaciones, usando solo features reales provenientes de snapshots RED3.
        prompt = f"""
Necesito que generes recomendaciones PERSONALIZADAS para un docente, basadas en métricas reales (últimos 7 y 30 días) y su estilo.

REGLAS:
- Devuelve SOLO JSON válido.
- Debes devolver EXACTAMENTE estas claves:
  - cards: array de 6 elementos
  - recomendaciones: array de 8 elementos
- Cada elemento debe tener:
  - id (string)
  - tipo (string corto)
  - titulo (string)
  - descripcion (string claro)
  - features_used (array de strings con los nombres EXACTOS de los features que usaste)

IMPORTANTE:
- En features_used SOLO puedes usar nombres reales que aparezcan en:
  snapshot_7d.features
  snapshot_30d.features
- No inventes nombres.
- No pongas valores, solo los nombres de features utilizados para construir esa card.

DATOS:
- style_main: {style_main}
- style_probs: {json.dumps(style_probs or {}, ensure_ascii=False)}
- confidence: {confidence}
- events_count: {events_count}
- data_strength: {data_strength}
- snapshot_7d.features: {json.dumps(features_7d or {}, ensure_ascii=False)}
- snapshot_30d.features: {json.dumps(features_30d or {}, ensure_ascii=False)}

SALIDA JSON:
{{
  "cards": [
    {{
      "id": "c1",
      "tipo": "...",
      "titulo": "...",
      "descripcion": "...",
      "features_used": ["feature_name_1","feature_name_2"]
    }}
  ],
  "recomendaciones": [
    {{
      "id": "r1",
      "tipo": "...",
      "titulo": "...",
      "descripcion": "...",
      "features_used": ["feature_name_1"]
    }}
  ]
}}
"""

        # Genera la salida con el LLM y la convierte a una estructura JSON segura antes
        # de enviarla al frontend o guardarla en caché.
        llm_text = await self.llm.generate(prompt=prompt, context_chunks=[], history=[])
        parsed = _safe_parse_json(llm_text)

        # Se normaliza la salida del LLM para asegurar cantidad mínima y estructura
        # consistente de cards y recomendaciones, aunque la respuesta venga incompleta.
        cards_raw = _ensure_recs_list(parsed.get("cards"))
        recs_raw = _ensure_recs_list(parsed.get("recomendaciones"))

        # Normalizamos para asegurar contrato del front
        cards = [_normalize_item(x, f"c-{i+1}") for i, x in enumerate(cards_raw[:6])]
        while len(cards) < 6:
            cards.append(_normalize_item({}, f"c-{len(cards)+1}"))

        recs = [_normalize_item(x, f"r-{i+1}") for i, x in enumerate(recs_raw[:8])]
        while len(recs) < 8:
            recs.append(_normalize_item({}, f"r-{len(recs)+1}"))

        payload = {"cards": cards, "recomendaciones": recs}

        # Guarda la salida generada en caché persistente con expiración de 3 días.
        # Si esta escritura falla, no se rompe el flujo principal de recomendaciones.
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=3)).isoformat()

        cache_row = {
            "docente_id": docente_id,
            "window_days": int(window_days),
            "period_end": period_end,
            "generated_at": now.isoformat(),
            "expires_at": expires_at,
            "payload": payload,
        }
        try:
            await self.cache.upsert(access_token, cache_row)
        except Exception:
            pass

        # Devuelve el perfil, snapshots y recomendaciones ya listas para consumo
        # inmediato desde la UI del módulo adaptativo.
        return {
            "profile": prof,
            "snapshot_7d": snap7,
            "snapshot_30d": snap30,
            "cards": cards,
            "recomendaciones": recs,
            "meta": {
                "cached": False,
                "generated_at": now.isoformat(),
                "expires_at": expires_at,
                "period_end": period_end,
                "window_days": int(window_days),
            },
        }