# app/infrastructure/ai/model_r2_loader.py

# Este archivo define la clase ModelR2Loader, que se encarga de cargar modelos de IA desde un almacenamiento R2 compatible con S3.
# Utiliza boto3 para interactuar con el servicio de almacenamiento, descargando los archivos del modelo a un directorio local 
# si no están presentes. La clase se inicializa con las credenciales y configuración de R2 obtenidas desde las variables de entorno definidas en settings.py.
# Proporciona un método ensure_model_dir que verifica la presencia de los archivos requeridos y los descarga si es necesario, 
# asegurando que el modelo esté listo para ser cargado por los clasificadores RED1, RED2 o RED3.

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import logging

import boto3
from botocore.client import Config

from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class ModelR2Loader:
    def __init__(self) -> None:
        if not all([
            settings.R2_ENDPOINT,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_BUCKET,
        ]):
            raise RuntimeError("Faltan variables de entorno de R2.")

        self.bucket = settings.R2_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )

    def ensure_model_dir(self, local_dir: str | Path, r2_prefix: str, required_files: Iterable[str]) -> None:
        local_path = Path(local_dir)
        local_path.mkdir(parents=True, exist_ok=True)

        missing_files = [name for name in required_files if not (local_path / name).exists()]
        if not missing_files:
            logger.info("[R2] Modelo ya disponible localmente: %s", local_path)
            return

        logger.info("[R2] Faltan archivos en %s. Descargando desde %s...", local_path, r2_prefix)

        for filename in required_files:
            target_file = local_path / filename
            if target_file.exists():
                continue

            object_key = f"{r2_prefix.rstrip('/')}/{filename}"
            logger.info("[R2] Descargando %s -> %s", object_key, target_file)
            self.client.download_file(self.bucket, object_key, str(target_file))

        logger.info("[R2] Descarga completa para %s", local_path)