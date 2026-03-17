# app/infrastructure/ai/red2_classifier.py

# Componente de infraestructura encargado de cargar y ejecutar la RED2 del sistema.
# Esta red combina embeddings del texto con señales de RED1 y metadatos simples
# para recomendar tipos de recursos pedagógicos. Sus artefactos se cargan desde
# la carpeta del modelo exportado correspondiente (por ejemplo `red2_model`).
from __future__ import annotations

import json
import os
import re
import numpy as np
import torch
import torch.nn as nn

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer

# Estructura de salida de RED2: Ranking top de etiquetas sugeridas y mapa
# completo de probabilidades por clase.
@dataclass
class Red2Output:
    top: List[Dict[str, Any]]   # [{"label":"ACTIVIDAD_PRACTICA","p":0.62}, ...]
    probs: Dict[str, float]     # {"VIDEO":0.1, ...}

# Arquitectura base de RED2: Clasificador MLP que recibe un vector híbrido
# construido a partir de embeddings y señales auxiliares.
class _MLPClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, dropout: float = 0.2):
        super().__init__()
        
        # Red densa de varias capas que transforma el vector de entrada en logits
        # para las clases objetivo de RED2.
        self.net = nn.Sequential(
            nn.Linear(input_dim, 512), # Primera capa densa que expande el espacio de características.
            nn.ReLU(), # Función de activación no lineal para introducir complejidad en el modelo.
            nn.Dropout(dropout), # Capa de dropout para reducir el sobreajuste durante el entrenamiento.
            nn.Linear(512, 128), # Segunda capa densa que reduce la dimensionalidad antes de la capa de salida.
            nn.ReLU(), # Función de activación no lineal para introducir complejidad en el modelo.
            nn.Dropout(dropout), # Capa de dropout para reducir el sobreajuste durante el entrenamiento.
            nn.Linear(128, num_classes), # Capa de salida que produce logits para cada clase objetivo de RED2.
        )

    def forward(self, x):
        return self.net(x) # El método forward define cómo se propaga la información a través de la red para generar los logits de salida.

# Wrapper de inferencia de RED2. Se encarga de cargar configuración, boosts,
# modelo SBERT y pesos entrenados para producir sugerencias de recursos.
class Red2Classifier:
    def __init__(self, model_dir: str):
        self.model_dir = os.path.abspath(model_dir)

        # Rutas de los artefactos exportados de RED2. Deben existir dentro del
        # directorio del modelo cargado (red2_model).
        cfg_path = os.path.join(self.model_dir, "config.json")
        boosts_path = os.path.join(self.model_dir, "intent_boosts.json")
        state_path = os.path.join(self.model_dir, "mlp_state.pt")

        # Valida la presencia mínima de archivos necesarios para poder ejecutar la red.
        if not os.path.exists(cfg_path):
            raise RuntimeError(f"[RED2] Falta config.json: {cfg_path}")
        if not os.path.exists(state_path):
            raise RuntimeError(f"[RED2] Falta mlp_state.pt: {state_path}")

        # Carga configuración estructural de RED2: Etiquetas, orden de features,
        # pesos internos y dimensiones esperadas del vector de entrada.
        with open(cfg_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)

        self.labels: List[str] = self.cfg["labels"]
        self.label2id = {l: i for i, l in enumerate(self.labels)}

        self.area_order: List[str] = self.cfg["area_order"]
        self.area2idx = {a: i for i, a in enumerate(self.area_order)}
        self.dim_order: List[str] = self.cfg["dim_order"]

        self.w_area = float(self.cfg.get("w_area", 1.0))
        self.w_dims = float(self.cfg.get("w_dims", 1.0))
        self.post_alpha = float(self.cfg.get("post_alpha", 0.85))

        self.input_dim = int(self.cfg["input_dim"])
        self.sbert_name = self.cfg["sbert_name"]

        # Carga boosts opcionales por intención textual. Estos patrones permiten
        # ajustar las probabilidades finales de RED2 según ciertas consultas.

        # Cada boost es un patrón regex asociado a un conjunto de etiquetas y pesos a sumar
        # a esas etiquetas cuando el patrón coincida con la consulta. 
        # Esto se aplica en la etapa de postprocesamiento de las probabilidades 
        # para reforzar o debilitar ciertas clases según la presencia de palabras 
        # clave en la consulta del usuario. 
        self.intent_boosts: List[Tuple[re.Pattern, Dict[str, float]]] = []
        if os.path.exists(boosts_path):
            with open(boosts_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw:
                pat = re.compile(item["pattern"], flags=re.IGNORECASE)
                adds = {k: float(v) for k, v in (item.get("adds") or {}).items()}
                self.intent_boosts.append((pat, adds))

        # Carga el encoder SBERT y el clasificador MLP entrenado, dejando ambos listos
        # para inferencia en CPU o GPU según disponibilidad.
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.sbert = SentenceTransformer(self.sbert_name, device=self.device)

        self.mlp = _MLPClassifier(self.input_dim, len(self.labels), dropout=0.2).to(self.device)
        st = torch.load(state_path, map_location=self.device)
        self.mlp.load_state_dict(st)
        self.mlp.eval()

    # Convierte la salida top de áreas de RED1 en un vector numérico alineado con
    # el orden de áreas esperado por RED2.
    def _build_area_vec(self, areas_top: Optional[List[Dict[str, Any]]]) -> np.ndarray:
        A = np.zeros(len(self.area_order), dtype=np.float32)
        if isinstance(areas_top, list):
            for it in areas_top:
                area = it.get("area")
                score = float(it.get("score", 0.0) or 0.0)
                if area in self.area2idx:
                    A[self.area2idx[area]] = score
        return A

    # Convierte las probabilidades por dimensión provenientes de RED1 en el vector
    # que RED2 utiliza como parte de su entrada.
    def _build_dims_vec(self, dims_probs: Optional[Dict[str, Any]]) -> np.ndarray:
        D = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float32)
        if isinstance(dims_probs, dict):
            D = np.array([float(dims_probs.get(k, 0.25) or 0.25) for k in self.dim_order], dtype=np.float32)
        return D

    # Codifica el tipo de fuente en una señal simple para que RED2 distinga entre,
    # por ejemplo, mensajes y archivos.
    def _build_tipo_vec(self, tipo_fuente: str) -> np.ndarray:
        t = (tipo_fuente or "").lower().strip()
        return np.array([1.0 if t == "mensaje" else 0.0], dtype=np.float32)

    # Genera una señal auxiliar simple basada en la longitud relativa del texto. 
    def _build_meta_vec(self, text: str) -> np.ndarray:
        L = min(len(text or "") / 800.0, 1.0)
        return np.array([float(L)], dtype=np.float32)

    # Implementación auxiliar de softmax en NumPy para el postprocesamiento final. 
    def _softmax_np(self, x: np.ndarray) -> np.ndarray:
        x = x.astype(np.float32)
        x = x - x.max()
        ex = np.exp(x)
        return ex / (ex.sum() + 1e-9)

    # Ajusta las probabilidades iniciales de RED2 aplicando boosts por intención
    # textual cuando la consulta coincide con patrones definidos.
    def _postprocess(self, probs: np.ndarray, query_text: Optional[str]) -> np.ndarray:
        p = probs.astype(np.float32)
        p = p / (p.sum() + 1e-9)

        if not query_text or not self.intent_boosts:
            return p

        boost = np.zeros_like(p, dtype=np.float32)
        q = query_text.strip().lower()

        for pat, adds in self.intent_boosts:
            if pat.search(q):
                for lbl, w in adds.items():
                    if lbl in self.label2id:
                        boost[self.label2id[lbl]] += float(w)

        logits = np.log(p + 1e-9) + (self.post_alpha * boost)
        return self._softmax_np(logits)

    def predict(
        self,
        text: str,
        areas_top: Optional[List[Dict[str, Any]]] = None,
        dims_probs: Optional[Dict[str, Any]] = None,
        tipo_fuente: str = "archivo",
        top_k: int = 5,
        query_for_post: Optional[str] = None,
    ) -> Red2Output:
        # Si el texto está vacío, devuelve una distribución uniforme para evitar fallos
        # y mantener un contrato de salida válido.
        text = (text or "").strip()
        if not text:
            probs = np.ones(len(self.labels), dtype=np.float32) / len(self.labels)
            idx = np.argsort(probs)[::-1][:top_k]
            top = [{"label": self.labels[i], "p": float(probs[i])} for i in idx]
            return Red2Output(top=top, probs={self.labels[i]: float(probs[i]) for i in range(len(self.labels))})

        # Genera el embedding SBERT del texto, que constituye la parte principal del
        # vector de entrada de RED2.
        e = self.sbert.encode([text], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)[0]

        # Construye las señales auxiliares que acompañan al embedding: áreas, dimensiones,
        # tipo de fuente y una métrica simple del texto.
        A = self._build_area_vec(areas_top) * float(self.w_area)
        D = self._build_dims_vec(dims_probs) * float(self.w_dims)
        T = self._build_tipo_vec(tipo_fuente)
        M = self._build_meta_vec(text) # Esta señal puede ayudar a RED2 a ajustar sus predicciones según la longitud del texto.

        # Une todas las señales en un único vector de entrada compatible con la arquitectura.
        x = np.concatenate([e, A, D, T, M], axis=0).astype(np.float32)
        xb = torch.tensor(x, dtype=torch.float32).unsqueeze(0).to(self.device)

        # Ejecuta el clasificador MLP y obtiene la distribución inicial de probabilidades.
        with torch.no_grad():
            logits = self.mlp(xb)[0]
            probs = torch.softmax(logits, dim=0).detach().cpu().numpy().astype(np.float32)

        # Aplica el postprocesamiento opcional, ordena las etiquetas más probables y
        # devuelve tanto el top-k como el mapa completo de probabilidades.
        probs2 = self._postprocess(probs, query_for_post)

        idx = np.argsort(probs2)[::-1][:top_k]
        top = [{"label": self.labels[i], "p": float(probs2[i])} for i in idx]
        probs_map = {self.labels[i]: float(probs2[i]) for i in range(len(self.labels))}
        return Red2Output(top=top, probs=probs_map)
