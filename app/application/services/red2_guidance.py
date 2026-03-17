# app/application/services/red2_guidance.py

# Servicio de aplicación de RED2 encargado de construir una guía didáctica
# resumida a partir de etiquetas ya inferidas sobre los chunks recuperados
# por RAG. Combina resultados de varios fragmentos, los pondera por relevancia
# y devuelve una instrucción breve utilizable dentro del prompt del LLM.

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

# Este servicio no clasifica texto directamente; reutiliza resultados ya
# guardados por RED2 para sintetizar una orientación pedagógica compacta.
class Red2GuidanceService:
    def __init__(self, red2_repo):
        self.red2_repo = red2_repo

    # Obtiene el peso de un resultado recuperado, priorizando score_ponderado,
    # similitud o score según lo que venga disponible en la fuente.
    def _weight_of(self, r: Dict[str, Any]) -> float:
        for k in ["score_ponderado", "similitud", "score"]:
            v = r.get(k)
            if isinstance(v, (int, float)):
                return float(v)
        return 1.0

    # Combina múltiples listas de etiquetas RED2 en una sola distribución agregada,
    # ponderando cada lista según la relevancia del chunk del que proviene.
    def _merge_top(self, tops: List[List[Dict[str, Any]]], weights: List[float]) -> List[Tuple[str, float]]:
        acc: Dict[str, float] = {}
        for top, w in zip(tops, weights):
            for item in (top or []):
                lbl = item.get("label")
                p = item.get("p")
                if not lbl or not isinstance(p, (int, float)):
                    continue
                acc[lbl] = acc.get(lbl, 0.0) + (float(p) * float(w))

        total = sum(acc.values()) or 1.0
        out = [(k, v / total) for k, v in acc.items()]
        out.sort(key=lambda x: x[1], reverse=True)
        return out

    async def build_guidance_from_rag_resultados(
        self,
        access_token: str,
        resultados: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> Optional[str]:
        if not resultados:
            return None

        # Recupera desde la base de datos las etiquetas RED2 asociadas a los chunks
        # que fueron devueltos por la búsqueda RAG.
        embedding_ids = [str(r.get("id")) for r in resultados if r.get("id")]
        rows = await self.red2_repo.fetch_chunk_labels_by_embedding_ids(access_token, embedding_ids)
        if not rows:
            return None

        m = {str(x.get("embedding_texto_id")): x.get("red2_top") for x in rows}

        # Empareja cada chunk recuperado con sus etiquetas RED2 y con el peso que
        # tendrá dentro de la mezcla final.
        tops = []
        weights = []
        for r in resultados:
            eid = str(r.get("id") or "")
            top = m.get(eid)
            if top:
                tops.append(top)
                weights.append(self._weight_of(r))

        if not tops:
            return None

        # Fusiona las etiquetas de todos los chunks y conserva solo las más relevantes
        # para construir una guía compacta.
        merged = self._merge_top(tops, weights)[:top_k]
        if not merged:
            return None

        # Convierte la mezcla final de etiquetas en una instrucción breve que luego
        # puede inyectarse en el prompt del LLM como guidance didáctica.
        parts = [f"{lbl} ({p:.2f})" for lbl, p in merged]
        return "Prioriza el tipo de recurso sugerido: " + ", ".join(parts) + "."
