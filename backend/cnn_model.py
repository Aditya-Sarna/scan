"""CNN inference engine — trained MLP heads on frozen MobileNetV3-Small features.

Each dataset has its own trained classifier head at /app/backend/weights/{ds_id}.pt,
produced by trainer.py on real Kaggle images.

Inference:
  x = preprocess(image)
  feat = backbone(x)           # frozen MobileNetV3-Small (ImageNet) → 576-D
  logits = head[ds_id](feat)   # trained MLP → num_classes
  probs = softmax(logits)

This is real supervised classification on real-world medical imagery.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Dict, List

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as M
import torchvision.transforms as T
from PIL import Image

from datasets import DATASETS
from sample_generator import ensure_all_samples


ROOT = Path(__file__).parent
WEIGHTS_DIR = ROOT / "weights"

DEVICE = torch.device("cpu")
FEATURE_DIM = 576


def _build_backbone() -> nn.Module:
    weights = M.MobileNet_V3_Small_Weights.DEFAULT
    m = M.mobilenet_v3_small(weights=weights)
    m.classifier = nn.Identity()
    m.eval()
    for p in m.parameters():
        p.requires_grad_(False)
    return m


class Head(nn.Module):
    def __init__(self, num_classes: int, in_dim: int = FEATURE_DIM, hidden: int = 256, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden, num_classes),
        )

    def forward(self, x):
        return self.net(x)


_backbone: nn.Module | None = None
_transform: T.Compose | None = None
_heads: Dict[str, Head] = {}
_class_order: Dict[str, List[str]] = {}
_val_accs: Dict[str, float] = {}


def _get_backbone() -> nn.Module:
    global _backbone, _transform
    if _backbone is None:
        _backbone = _build_backbone().to(DEVICE)
        weights = M.MobileNet_V3_Small_Weights.DEFAULT
        _transform = weights.transforms()
    return _backbone


def _preprocess(image_bytes: bytes) -> torch.Tensor:
    _get_backbone()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return _transform(img).unsqueeze(0).to(DEVICE)


def _extract(image_bytes: bytes) -> torch.Tensor:
    x = _preprocess(image_bytes)
    with torch.no_grad():
        feat = _get_backbone()(x)
    return F.normalize(feat, dim=1).squeeze(0)


def _load_head(dataset_id: str) -> bool:
    ckpt_path = WEIGHTS_DIR / f"{dataset_id}.pt"
    if not ckpt_path.exists():
        return False
    ckpt = torch.load(str(ckpt_path), map_location=DEVICE, weights_only=False)
    classes = ckpt["class_order"]
    head = Head(num_classes=len(classes))
    head.load_state_dict(ckpt["state_dict"])
    head.eval()
    _heads[dataset_id] = head
    _class_order[dataset_id] = classes
    _val_accs[dataset_id] = float(ckpt.get("val_acc", 0.0))
    return True


def warmup() -> None:
    ensure_all_samples()
    _get_backbone()
    for ds_id in DATASETS.keys():
        ok = _load_head(ds_id)
        if not ok:
            print(f"[cnn_model] WARNING: no trained head for {ds_id}; predictions disabled")


def predict(dataset_id: str, image_bytes: bytes, top_k: int = 3) -> dict:
    if dataset_id not in _heads:
        warmup()
    if dataset_id not in _heads:
        raise ValueError(f"No trained head for dataset_id: {dataset_id}")

    head = _heads[dataset_id]
    classes = _class_order[dataset_id]
    K = len(classes)

    feat = _extract(image_bytes)           # [576]
    with torch.no_grad():
        logits = head(feat.unsqueeze(0))   # [1, K]
        probs = F.softmax(logits, dim=1).squeeze(0)  # [K]

    order = torch.argsort(probs, descending=True).tolist()

    top: list[dict] = []
    for idx in order[: max(top_k, 1)]:
        top.append({
            "class_id": classes[idx],
            "label": DATASETS[dataset_id]["class_labels"][classes[idx]],
            "probability": float(probs[idx].item()),
            "similarity": float(logits[0, idx].item()),  # raw logit, handy for debugging
        })

    confidence = float(probs[order[0]].item())
    train_val_acc = _val_accs.get(dataset_id, 0.0)

    return {
        "dataset_id": dataset_id,
        "predicted_class": classes[order[0]],
        "predicted_label": DATASETS[dataset_id]["class_labels"][classes[order[0]]],
        "confidence": confidence,
        "top_k": top,
        "logits": [float(probs[i].item()) for i in range(K)],
        "model_arch": f"MobileNetV3-Small (ImageNet, frozen) → Linear-256-ReLU-Dropout-Linear head (Kaggle fine-tuned, val_acc={train_val_acc:.2f})",
    }
