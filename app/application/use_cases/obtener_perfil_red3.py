# app/application/use_cases/obtener_perfil_red3.py

# Use case del flujo de RED3 y PERFIL. Se encarga de recuperar el snapshot
# reciente del docente (7 y 30 días), su perfil adaptativo actual y un bloque
# de insights interpretables construidos a partir de features agregadas.

from __future__ import annotations
from typing import Dict, Any

# Este use case concentra la lectura del estado actual de RED3 para mostrar al
# frontend una vista resumida del comportamiento y estilo detectado del docente.
class ObtenerPerfilRed3UseCase:
    def __init__(self, auth_client, red3_service):
        self.auth = auth_client
        self.red3 = red3_service

    async def execute(self, access_token: str) -> Dict[str, Any]:
        # Primero identifica al docente autenticado y recupera tanto sus snapshots como
        # su perfil RED3 actual desde el repositorio.
        user = await self.auth.get_user(access_token)
        docente_id = user["id"]

        snap_30 = await self.red3.repo.get_latest_snapshot(access_token, docente_id, window_days=30)
        snap_7 = await self.red3.repo.get_latest_snapshot(access_token, docente_id, window_days=7)
        profile = await self.red3.repo.get_style_profile(access_token, docente_id)

        # Los insights interpretables se construyen principalmente sobre las features
        # del snapshot de 30 días, que representa la ventana más estable del perfil.
        features_30 = (snap_30 or {}).get("features") or {}

        # Devuelve la información estructurada del perfil junto con una interpretación
        # más legible pensada para consumo directo desde frontend.
        return {
            "ok": True,
            "docente_id": docente_id,
            "period_end": (snap_30 or {}).get("period_end") or (snap_7 or {}).get("period_end"),
            "snap_30d": snap_30,
            "snap_7d": snap_7,
            "profile": profile,
            "insights": self._interpret(features_30),
        }

    # Traduce un conjunto de features numéricas de RED3 a insights más humanos
    # y resumidos para facilitar su lectura en la interfaz.
    def _interpret(self, f: Dict[str, Any]) -> Dict[str, Any]:
        if not f:
            return {
                "status": "no_data",
                "message": "Aún no hay suficientes eventos para construir insights.",
            }

        # Convierte features a float de forma segura para evitar errores por valores
        # nulos, cadenas o tipos inesperados en los snapshots.
        def ffloat(k: str) -> float:
            try:
                return float(f.get(k, 0) or 0)
            except Exception:
                return 0.0

        # Convierte features a entero de forma segura para métricas de conteo.
        def fint(k: str) -> int:
            try:
                return int(f.get(k, 0) or 0)
            except Exception:
                return 0

        # Extrae las métricas principales que luego se resumirán en etiquetas e insights
        # interpretables sobre diversidad, tendencia evaluativa, fricción y dimensiones.

        ratio = ffloat("resource_tech_ratio_30d") # proporcion entre recursos técnicos (archivos, plantillas) y recursos totales usados en 30 días
        resources = fint("resources_suggested_30d")  # cantidad de recursos (archivos) sugeridos al docente en los últimos 30 días
        chat_eval = ffloat("chat_intent_eval_ratio_30d") # proporción de mensajes con intención evaluativa detectada en conversaciones del docente en los últimos 30 días
        friction = ffloat("friction_ratio_30d") # proporción de fricción detectada en la actividad del docente en los últimos 30 días

        dim_saber = ffloat("dim_saber_avg_30d") # promedio de la dimensión SABER en los recursos usados por el docente en los últimos 30 días
        dim_hacer = ffloat("dim_hacer_avg_30d") # promedio de la dimensión HACER en los recursos usados por el docente en los últimos 30 días
        dim_ser = ffloat("dim_ser_avg_30d") # promedio de la dimensión SER en los recursos usados por el docente en los últimos 30 días
        dim_decidir = ffloat("dim_decidir_avg_30d") # promedio de la dimensión DECIDIR en los recursos usados por el docente en los últimos 30 días

        # Resume la diversidad temática del uso de recursos según el ratio calculado
        # previamente en los snapshots de RED3.
        if ratio > 0.8:
            diversity_label = "Alta concentración temática"
        elif ratio > 0.4:
            diversity_label = "Balance temático"
        else:
            diversity_label = "Alta diversidad temática"

        # Determina qué dimensión del modelo educativo tiene mayor presencia promedio
        # en la actividad reciente del docente.
        dims = {"SABER": dim_saber, "HACER": dim_hacer, "SER": dim_ser, "DECIDIR": dim_decidir}
        main_dimension = max(dims, key=dims.get) if dims else None

        # Construye observaciones simples y legibles a partir de umbrales fijos sobre
        # las métricas más relevantes del snapshot de 30 días.
        hints = []
        if resources >= 6:
            hints.append("Uso intensivo de recursos en el último mes.")
        elif resources > 0:
            hints.append("Uso moderado de recursos en el último mes.")
        else:
            hints.append("Aún no se detecta uso de recursos (archivos) en el último mes.")

        if chat_eval >= 0.4:
            hints.append("Tendencia evaluativa alta en tus conversaciones.")
        if friction >= 0.3:
            hints.append("Se detecta fricción: conviene sugerir plantillas más directas y cortas.")

        # Devuelve una lectura resumida del estado del docente en formato más amigable
        # para paneles, tarjetas o explicaciones del frontend.
        return {
            "status": "ok",
            "diversity_label": diversity_label,
            "main_dimension": main_dimension,
            "resources_used_30d": resources,
            "evaluative_tendency_30d": chat_eval,
            "friction_level_30d": friction,
            "hints": hints,
        }