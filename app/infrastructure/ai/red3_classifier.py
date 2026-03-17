# app/infrastructure/ai/red3_classifier.py

# Componente de infraestructura encargado de cargar y ejecutar la RED3 del sistema.
# Esta red recibe features agregadas del comportamiento del docente, las normaliza
# con los artefactos exportados y predice el estilo pedagógico principal junto con
# sus probabilidades. Sus artefactos se cargan desde la carpeta del modelo exportado
# correspondiente (red3_model).
from __future__ import annotations

import json
import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Arquitectura base de RED3: MLP profundo usado para clasificar el estilo del
# docente a partir de features agregadas.
class Red3MLP(nn.Module):
    def __init__(self, in_dim: int, num_classes: int):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 32)
        self.out = nn.Linear(32, num_classes)
        self.drop = nn.Dropout(p=0.25)

    # Propagación por capas densas con activación ReLU y dropout para producir los logits finales.
    def forward(self, x):
        x = F.relu(self.fc1(x)); x = self.drop(x) 
        x = F.relu(self.fc2(x)); x = self.drop(x)
        x = F.relu(self.fc3(x)); x = self.drop(x)
        return self.out(x)

# Estructura de salida de RED3: Estilo principal predicho, probabilidades por estilo
# y nivel de confianza de la predicción.
@dataclass 
class Red3Pred:
    style_main: str
    style_probs: Dict[str, float]
    confidence: float

# Wrapper de inferencia de RED3. Se encarga de cargar configuración, schema de
# features, scaler, mapa de etiquetas y pesos entrenados para exponer una
# predicción estable del perfil docente.
class Red3Classifier:
    """
    Artefactos esperados:
      - red3_config.json
      - red3_feature_schema.json
      - red3_scaler.json
      - red3_label_map.json
      - red3_model_state.pt
    """

    def __init__(self, model_dir: str, device: Optional[str] = None):
        self.model_dir = os.path.abspath(model_dir)

        # Rutas de los artefactos exportados de RED3. Deben existir dentro del
        # directorio del modelo cargado (red3_model).
        cfg_path = os.path.join(self.model_dir, "red3_config.json")
        schema_path = os.path.join(self.model_dir, "red3_feature_schema.json")
        scaler_path = os.path.join(self.model_dir, "red3_scaler.json")
        label_map_path = os.path.join(self.model_dir, "red3_label_map.json")
        state_path = os.path.join(self.model_dir, "red3_model_state.pt")

        # Verifica que estén presentes todos los artefactos necesarios antes de
        # intentar cargar el modelo.
        for p in [cfg_path, schema_path, scaler_path, label_map_path, state_path]:
            if not os.path.exists(p):
                raise FileNotFoundError(f"[RED3] Falta archivo requerido: {p}")

        # Load JSONs
        # Carga la configuración y los artefactos auxiliares exportados desde el
        # entrenamiento de RED3.
        with open(cfg_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)

        with open(schema_path, "r", encoding="utf-8") as f:
            raw_schema = json.load(f)

        with open(scaler_path, "r", encoding="utf-8") as f:
            self.scaler = json.load(f)

        with open(label_map_path, "r", encoding="utf-8") as f:
            raw_labels = json.load(f)

        # Parse labels 
        # Interpreta el mapa de etiquetas exportado para obtener el orden final de clases.
        self.labels: List[str] = self._parse_labels(raw_labels)
        if not self.labels:
            raise RuntimeError("[RED3] labels vacío (red3_label_map.json inválido).")

        # Parse feature schema 
        # Extrae el schema de features que define exactamente qué variables espera RED3.
        self.feature_names: List[str] = self._parse_feature_names(raw_schema)
        if not self.feature_names:
            raise RuntimeError("[RED3] feature_schema vacío (red3_feature_schema.json inválido).")

        # Valida que la dimensión esperada del modelo coincida con la cantidad real
        # de features exportadas en el schema (30).
        input_dim_schema = self._parse_input_dim(raw_schema, fallback=len(self.feature_names))
        self.input_dim = int(input_dim_schema)

        if self.input_dim != len(self.feature_names):
            raise RuntimeError(
                f"[RED3] len(feature_schema)({len(self.feature_names)}) != input_dim(schema)({self.input_dim}). "
                "Tus artefactos están inconsistentes."
            )

        # Scaler
        # Carga y valida los parámetros de normalización usados para escalar las features
        # antes de la inferencia. Estos parámetros deben haber sido exportados 
        # desde el entorno de entrenamiento.
        mean = np.array(self.scaler.get("mean", []), dtype=np.float32)
        std = np.array(self.scaler.get("std", []), dtype=np.float32)

        if mean.shape[0] != self.input_dim or std.shape[0] != self.input_dim:
            raise RuntimeError(
                f"[RED3] scaler mean/std no coincide con input_dim={self.input_dim}. "
                f"mean={mean.shape}, std={std.shape}"
            )

        std = np.where(std < 1e-8, 1.0, std)
        self.mean = mean
        self.std = std

        # Reconstruye la arquitectura de RED3, carga los pesos exportados y deja
        # el modelo en modo evaluación.
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model = Red3MLP(self.input_dim, len(self.labels)).to(self.device)
        st = torch.load(state_path, map_location=self.device)

        self.model.load_state_dict(st, strict=True)
        self.model.eval()

    # Interpreta distintos formatos posibles del mapa de etiquetas exportado para
    # obtener una lista ordenada de labels.
    def _parse_labels(self, raw: Any) -> List[str]:
        # Caso Colab actual: {"labels": [...]}
        if isinstance(raw, dict) and isinstance(raw.get("labels"), list):
            return [str(x) for x in raw["labels"]]

        # Caso legacy: {"0":"REFLEXIVO", ...}
        if isinstance(raw, dict) and raw and all(str(k).isdigit() for k in raw.keys()):
            id2label = {int(k): str(v) for k, v in raw.items()}
            return [id2label[i] for i in sorted(id2label.keys())]

        # Caso legacy invertido: {"REFLEXIVO":0, ...}
        if isinstance(raw, dict) and raw:
            try:
                id2label = {int(v): str(k) for k, v in raw.items()}
                return [id2label[i] for i in sorted(id2label.keys())]
            except Exception:
                return []

        # Caso raro: lista directa
        if isinstance(raw, list):
            return [str(x) for x in raw]

        return []

    # Interpreta distintos formatos posibles del schema de features y extrae
    # únicamente los nombres esperados por el modelo.
    def _parse_feature_names(self, raw_schema: Any) -> List[str]:
        # Caso Colab actual: dict con features:[{name,type}]
        if isinstance(raw_schema, dict) and isinstance(raw_schema.get("features"), list):
            feats = raw_schema["features"]
            names = []
            for it in feats:
                if isinstance(it, dict) and it.get("name"):
                    names.append(str(it["name"]))
            return names

        # Caso simple: lista ["f1","f2"...]
        if isinstance(raw_schema, list):
            return [str(x) for x in raw_schema]

        return []

    # Obtiene la dimensión de entrada esperada desde el schema, usando un fallback
    # si no está definida explícitamente.
    def _parse_input_dim(self, raw_schema: Any, fallback: int) -> int:
        if isinstance(raw_schema, dict) and raw_schema.get("input_dim") is not None:
            try:
                return int(raw_schema["input_dim"])
            except Exception:
                pass
        return int(fallback)

    # Convierte el diccionario de features agregadas en un vector numérico alineado
    # con el schema exportado y luego lo normaliza con mean/std del scaler.
    def _vectorize_features(self, feats: Dict[str, Any]) -> np.ndarray:
        x = np.zeros(self.input_dim, dtype=np.float32)
        for i, name in enumerate(self.feature_names):
            v = feats.get(name, 0.0)
            try:
                x[i] = float(v)
            except Exception:
                x[i] = 0.0
        # scale
        x = (x - self.mean) / self.std
        return x.astype(np.float32)

    @torch.no_grad() # Desactiva el cálculo de gradientes para optimizar la inferencia, ya que no se necesitan para la predicción.
    
    # Ejecuta la inferencia completa de RED3 a partir de features agregadas del docente
    # y devuelve el estilo principal, probabilidades por clase y confianza.
    def predict(self, features: Dict[str, Any]) -> Red3Pred:
        x = self._vectorize_features(features)
        xb = torch.tensor(x, dtype=torch.float32).unsqueeze(0).to(self.device)

        # Ejecuta la red y convierte los logits a probabilidades por estilo usando softmax.
        logits = self.model(xb)[0]
        probs = torch.softmax(logits, dim=0).detach().cpu().numpy().astype(np.float32)

        # Selecciona la clase dominante y construye la salida final reutilizable por
        # RED3Service y otros flujos del sistema.
        best = int(np.argmax(probs))
        style_main = self.labels[best]
        conf = float(probs[best])

        style_probs = {self.labels[i]: float(probs[i]) for i in range(len(self.labels))}
        return Red3Pred(style_main=style_main, style_probs=style_probs, confidence=conf)