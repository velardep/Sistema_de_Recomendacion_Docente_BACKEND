# app/application/services/red3_service.py

# Servicio de aplicación de RED3 encargado de registrar eventos del docente,
# ejecutar snapshots de features y actualizar el perfil adaptativo del usuario.
# Todo el flujo se maneja en modo best-effort para no romper chats, PDC ni
# otros procesos principales si RED3 falla de manera parcial.

from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import datetime, date, timezone

# Este servicio centraliza la escritura de eventos y la actualización del
# perfil RED3, separando la lógica adaptativa del resto de use cases.
class Red3Service:

    def __init__(self, red3_repo, red3_classifier):
        self.repo = red3_repo
        self.model = red3_classifier

    async def record_event_best_effort(
        self,
        access_token: str,
        *,
        docente_id: str,
        event_type: str,
        meta: Dict[str, Any],
        espacio_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        occurred_at: Optional[str] = None, 
    ) -> None:
        # Construye el payload base del evento con el tipo de acción detectada y su
        # metadata asociada para posterior análisis en snapshots.
        payload = {
            "docente_id": docente_id,
            "event_type": event_type,
            "meta": meta or {},
        }

        # Estos campos se guardan como contexto de primer nivel en la tabla de eventos,
        # no dentro de meta, para facilitar consultas y trazabilidad posterior.
        if espacio_id:
            payload["espacio_id"] = espacio_id
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if occurred_at:
            payload["occurred_at"] = occurred_at

        # El registro del evento es best-effort: Si falla, no debe romper el flujo
        # principal que generó dicho evento.
        try:
            await self.repo.insert_event(access_token, payload)
        except Exception:
            pass

    async def update_profile_best_effort(
        self,
        access_token: str,
        *,
        docente_id: str,
        period_end: Optional[str] = None,   # 'YYYY-MM-DD'
        window_days: int = 30,
    ) -> None:
        """
        Ejecuta:
        1) snapshots RPC
        2) lee snapshot latest
        3) predice
        4) upsert profile
        """
        # Si no se especifica una fecha de corte, se usa la fecha actual como referencia
        # para ejecutar snapshots y actualizar el perfil.
        if not period_end:
            period_end = datetime.now(timezone.utc).date().isoformat()

        # Primero ejecuta el pipeline de snapshots en base de datos. Si esa etapa falla,
        # no tiene sentido continuar con la actualización del perfil.
        ok = False
        try:
            ok = await self.repo.run_snapshots(access_token, docente_id, period_end)
        except Exception:
            ok = False

        if not ok:
            return

        # Recupera el snapshot más reciente para la ventana solicitada, que contiene
        # las features agregadas necesarias para la predicción de RED3.
        snap = None
        try:
            snap = await self.repo.get_latest_snapshot(access_token, docente_id, window_days=window_days)
        except Exception:
            snap = None

        if not snap:
            return

        # Verifica que el snapshot tenga una estructura válida de features antes de
        # intentar predecir el estilo del docente.
        features = snap.get("features") or {}
        if not isinstance(features, dict):
            return

        # Ejecuta la predicción del perfil adaptativo a partir de las features agregadas.
        try:
            pred = self.model.predict(features)
        except Exception:
            return

        # CALCULAR events_count y data_strength (SIN inventar datos)
        # - events_count sale SOLO de features que YA existen en snapshot
        # - data_strength se deriva de events_count de forma determinística
        def _num(x):
            try:
                return float(x)
            except Exception:
                return 0.0

        # Calcula cuánta actividad real tuvo el docente en la ventana analizada usando
        # únicamente métricas existentes en el snapshot, sin inventar datos adicionales.
        if int(window_days) == 7:
            chat_msgs = _num(features.get("chat_msgs_7d"))
            pdc_gen = _num(features.get("pdc_generated_7d"))
        else:
            chat_msgs = _num(features.get("chat_msgs_30d"))
            pdc_gen = _num(features.get("pdc_generated_30d"))

        up_cnt = _num(features.get("pdc_uploads_30d"))
        down_cnt = _num(features.get("pdc_downloads_30d"))
        del_cnt = _num(features.get("pdc_deletes_30d"))

        events_count = int(chat_msgs + pdc_gen + up_cnt + down_cnt + del_cnt)

        # data_strength: 0..1 en función de cuánta data real hay.
        # 50 eventos = "fuerte" (1.0). Menos = proporcional.
        # (Esto NO inventa datos: es una normalización determinística.)
        # Normaliza la cantidad de eventos a una escala 0..1 para estimar cuánta base
        # real de datos respalda el perfil calculado.
        data_strength = max(0.0, min(1.0, events_count / 50.0))

        # Construye el perfil final que se almacenará, incluyendo resultado del modelo
        # y métricas de soporte como events_count y data_strength.
        payload = {
            "docente_id": docente_id,
            "window_days": int(window_days),
            "feature_schema_version": 1,
            "model_version": "red3_v1",

            "style_main": pred.style_main,
            "style_probs": pred.style_probs,
            "confidence": float(pred.confidence),

            "data_strength": float(data_strength),
            "events_count": int(events_count),
        }

        # Guarda o actualiza el perfil RED3 del docente sin interrumpir el flujo si
        # la persistencia falla.
        try:
            await self.repo.upsert_style_profile(access_token, payload)
        except Exception:
            pass