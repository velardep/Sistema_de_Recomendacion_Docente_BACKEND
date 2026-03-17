# app/application/services/red1_service.py

# app/application/services/red1_service.py
# Servicio de aplicación de RED1 encargado de ejecutar la clasificación de texto
# y si es posible, guardar la inferencia en base de datos. Su diseño es
# best-effort: si el guardado falla, no interrumpe el flujo principal y aun así
# devuelve la salida de la red para que otras capas del sistema puedan usarla.

from __future__ import annotations
from typing import Any, Dict, Optional

# Este servicio encapsula la relación entre el clasificador de RED1 y el
# repositorio de persistencia, dejando un punto único para clasificar texto
# y registrar inferencias.
class Red1Service:
    def __init__(self, classifier, red1_repo):
        self.classifier = classifier
        self.repo = red1_repo

    async def clasificar_y_guardar(
        self,
        access_token: str,
        *,
        docente_id: str,
        espacio_id: Optional[str],
        conversacion_espacio_id: Optional[str],
        mensaje_espacio_id: Optional[str],
        tipo_fuente: str,          # 'mensaje'|'archivo'
        fuente_id: Optional[str],
        chunk_index: Optional[int],
        texto: str,
        texto_resumen_chars: int = 600,
    ) -> Optional[Dict[str, Any]]:
        """
        Devuelve un dict SIEMPRE que la inferencia haya sido posible:
        {
          "out": <salida completa de red1>,
          "areas_top": [...],
          "dims_probs": {...},
          "area_main": "...",
          "db_row": <fila insertada en red1_inferencias o None>
        }
        """
        # Primero ejecuta la inferencia de RED1. Si la clasificación falla, se devuelve
        # None porque sin salida de la red no hay nada útil que persistir ni propagar.
        try:
            out = self.classifier.classify_text(texto)
        except Exception:
            return None

        # Construye el payload de persistencia con trazabilidad del texto analizado,
        # contexto de origen y salida completa de la red.
        payload = {
            "docente_id": docente_id,
            "espacio_id": espacio_id,
            "conversacion_espacio_id": conversacion_espacio_id,
            "mensaje_espacio_id": mensaje_espacio_id,
            "tipo_fuente": tipo_fuente,
            "fuente_id": fuente_id,
            "chunk_index": chunk_index,
            "texto_resumen": (texto[:texto_resumen_chars] if texto else None),
            "texto_sha1": out.get("text_sha1"),
            "salida": out,
            "area": out.get("area_main"),
            "dims_probs": out.get("dims_probs"),
            "active": out.get("active"),
        }

        db_row = None
        try:
            db_row = await self.repo.insertar_inferencia(access_token, payload)
        except Exception:
            db_row = None

        # Devuelve siempre la parte más útil de la inferencia para que otros flujos,
        # como RED2, PDC o chat, puedan reutilizar las señales de RED1.
        return {
            "out": out,
            "areas_top": out.get("areas_top"),
            "dims_probs": out.get("dims_probs"),
            "area_main": out.get("area_main"),
            "db_row": db_row,
        }
