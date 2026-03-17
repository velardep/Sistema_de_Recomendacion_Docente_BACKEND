# app/infrastructure/ai/red1_classifier.py

# Componente de infraestructura encargado de cargar y ejecutar la RED1 del sistema (LSTM Multi-Head).
# Esta red clasifica texto pedagógico para estimar área principal, probabilidades
# por dimensión y combinaciones área-dimensión. Sus artefactos se cargan desde
# la carpeta del modelo exportado correspondiente (red1_model).
from __future__ import annotations

import os
import json
import hashlib
import numpy as np
import torch
import torch.nn as nn

from typing import Any, Dict, List, Optional
from transformers import AutoTokenizer

# Arquitectura base de la RED1: modelo LSTM bidireccional con dos salidas,
# una para áreas y otra para dimensiones pedagógicas.
class PedagogicalLSTMMultiHead(nn.Module):
    def __init__(self, vocab_size, pad_token_id, emb_dim, hidden_dim, num_areas, num_dims):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, emb_dim, padding_idx=pad_token_id)
        self.lstm = nn.LSTM(
            input_size=emb_dim,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True,
        )
        self.dropout = nn.Dropout(0.2)
        self.fc_area = nn.Linear(hidden_dim * 2, num_areas)
        self.fc_dim = nn.Linear(hidden_dim * 2, num_dims)

    # Convierte tokens en embeddings y luego procesa la secuencia completa con la LSTM.
    def forward(self, input_ids, attention_mask):
        x = self.embedding(input_ids)               # [B,T,E]
        out, _ = self.lstm(x)                       # [B,T,2H]

        # Aplica enmascarado para ignorar padding y resume la secuencia mediante media
        # enmascarada antes de pasar a las capas finales de clasificación.
        mask = attention_mask.unsqueeze(-1).float() # [B,T,1]
        out = out * mask
        pooled = out.sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)  # masked mean
        pooled = self.dropout(pooled)

        # Produce los logits independientes para área y dimensión, que luego serán
        # convertidos a probabilidades durante la inferencia.
        logits_area = self.fc_area(pooled)
        logits_dim = self.fc_dim(pooled)
        return logits_area, logits_dim

# Wrapper de inferencia de RED1. Se encarga de cargar tokenizer, configuración
# y pesos exportados desde entrenamiento, y exponer una salida estable para el sistema.
class Red1Classifier:

    def __init__(self, export_dir: str, device: str = "cpu"):
        self.export_dir = export_dir
        self.device = device

        # Rutas de los artefactos exportados de RED1. Estos archivos deben existir
        # dentro del directorio del modelo cargado (red1_model).
        cfg_path = os.path.join(export_dir, "config.json")
        tok_name_path = os.path.join(export_dir, "tokenizer_name.txt")
        weights_path = os.path.join(export_dir, "pedagogical_lstm.pt")

        # Valida que estén presentes los artefactos mínimos necesarios para ejecutar
        # la inferencia de RED1.
        if not os.path.exists(cfg_path):
            raise FileNotFoundError(f"No existe config.json en {export_dir}")
        if not os.path.exists(tok_name_path):
            raise FileNotFoundError(f"No existe tokenizer_name.txt en {export_dir}")
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"No existe pedagogical_lstm.pt en {export_dir}")

        # Carga la configuración del modelo y el tokenizer usado originalmente
        # durante el entrenamiento/exportación.
        self.cfg = json.load(open(cfg_path, encoding="utf-8"))
        tok_name = open(tok_name_path, encoding="utf-8").read().strip()
        self.tokenizer = AutoTokenizer.from_pretrained(tok_name)

        self.areas = self.cfg["areas"]
        self.dims = self.cfg["dims"]

        # Reconstruye la arquitectura de RED1 con los parámetros exportados, carga
        # los pesos entrenados y deja el modelo en modo evaluación.
        self.model = PedagogicalLSTMMultiHead(
            vocab_size=self.cfg["vocab_size"],
            pad_token_id=self.cfg["pad_token_id"],
            emb_dim=self.cfg["emb_dim"],
            hidden_dim=self.cfg["hidden_dim"],
            num_areas=len(self.areas),
            num_dims=len(self.dims),
        )

        sd = torch.load(weights_path, map_location=device)
        self.model.load_state_dict(sd, strict=True)
        self.model.to(device)
        self.model.eval()

    # Genera un hash estable del texto para trazabilidad de inferencias sin tener
    # que guardar el texto completo en todos los contextos.
    def _sha1(self, text: str) -> str:
        return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

    # Construye las combinaciones área__dimensión multiplicando las probabilidades
    # de ambas salidas para obtener un score conjunto por combinación.
    def _build_combo_scores(self, area_probs: np.ndarray, dim_probs: np.ndarray) -> List[Dict[str, float]]:
        combos = []
        for ai, a in enumerate(self.areas):
            for di, d in enumerate(self.dims):
                combos.append({"label": f"{a}__{d}", "score": float(area_probs[ai] * dim_probs[di])})
        combos.sort(key=lambda x: -x["score"])
        return combos
    
    # `@torch.no_grad()` desactiva el cálculo de gradientes dentro de este método.
    # Esto evita construir el grafo de autograd y que los tensores acumulen `.grad`.
    # Beneficios: reduce uso de memoria y acelera la ejecución en inferencia.
    # Nota: no sustituye a `model.eval()` (dropout/batchnorm); normalmente se usan juntos.
    @torch.no_grad()
    
    # Ejecuta la inferencia completa de RED1 sobre un texto y devuelve una salida
    # estructurada con área principal, rankings, probabilidades por dimensión,
    # combinaciones principales y combinaciones activas según threshold.
    def classify_text(self, text: str, threshold: Optional[float] = None) -> Dict[str, Any]:
        # Usa el threshold por defecto definido en los artefactos del modelo, salvo
        # que el flujo que lo llame especifique uno distinto.
        thr = self.cfg["threshold_default"] if threshold is None else float(threshold)

        # Tokeniza el texto de entrada usando la misma configuración de longitud máxima
        # con la que RED1 fue entrenada/exportada.
        enc = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.cfg["max_len"],
            return_tensors="pt",
        )
        ids = enc["input_ids"].to(self.device)
        att = enc["attention_mask"].to(self.device)

        # Ejecuta la red y convierte los logits a probabilidades independientes para
        # áreas y dimensiones usando sigmoid.
        logits_area, logits_dim = self.model(ids, att)
        area_probs = torch.sigmoid(logits_area).cpu().numpy()[0]
        dim_probs = torch.sigmoid(logits_dim).cpu().numpy()[0]

        # Construye una salida legible con ranking de áreas y mapa de probabilidades
        # por dimensión pedagógica.
        area_rank = sorted(
            [{"area": self.areas[i], "score": float(area_probs[i])} for i in range(len(self.areas))],
            key=lambda x: -x["score"],
        )
        dims_out = {self.dims[i]: float(dim_probs[i]) for i in range(len(self.dims))}

        # Calcula combinaciones área-dimensión, conserva las más fuertes y además
        # selecciona las combinaciones activas usando el threshold configurado.
        combo_scores = self._build_combo_scores(area_probs, dim_probs)
        top_combos = combo_scores[: self.cfg["top_k_combos"]]

        active = [c for c in combo_scores if c["score"] >= thr]
        if not active:
            active = [combo_scores[0]]
        active = active[: self.cfg["max_active_combos"]]

        # Área “principal” = top 1
        area_main = area_rank[0]["area"] if area_rank else None

        # Devuelve una estructura estable que luego puede ser persistida y reutilizada
        # por servicios como RED2 o por otros flujos del sistema.
        return {
            "threshold": thr,
            "area_main": area_main,
            "areas_top": area_rank[: self.cfg["top_areas"]],
            "dims_probs": dims_out,
            "combo_top": top_combos,
            "active": active,
            "text_sha1": self._sha1(text),
        }
