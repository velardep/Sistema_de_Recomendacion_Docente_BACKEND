# app/infrastructure/ai/ensure_models.py

# Este archivo se encarga de asegurar que los modelos de IA necesarios para RED1, RED2 y RED3 estén disponibles localmente.
# Utiliza la clase ModelR2Loader para verificar la presencia de los archivos del modelo en el sistema de archivos local y, si faltan, 
# los descarga desde un almacenamiento R2 compatible con S3 utilizando las credenciales configuradas en settings.py.

from __future__ import annotations

from app.infrastructure.ai.model_r2_loader import ModelR2Loader
from app.infrastructure.config.settings import settings


def ensure_models_downloaded() -> None:
    loader = ModelR2Loader()

    loader.ensure_model_dir(
        local_dir=settings.RED1_EXPORT_DIR,
        r2_prefix=settings.RED1_R2_PREFIX,
        required_files=[
            "config.json",
            "labels.json",
            "pedagogical_lstm.pt",
            "tokenizer_name.txt",
        ],
    )

    loader.ensure_model_dir(
        local_dir=settings.RED2_EXPORT_DIR,
        r2_prefix=settings.RED2_R2_PREFIX,
        required_files=[
            "config.json",
            "intent_boosts.json",
            "mlp_state.pt",
        ],
    )

    loader.ensure_model_dir(
        local_dir=settings.RED3_EXPORT_DIR,
        r2_prefix=settings.RED3_R2_PREFIX,
        required_files=[
            "red3_config.json",
            "red3_feature_schema.json",
            "red3_label_map.json",
            "red3_metrics.json",
            "red3_model_state.pt",
            "red3_scaler.json",
        ],
    )