"""CNN inference engine.

Pretrained MobileNetV3-Small (ImageNet) → 576-D feature.
Per dataset, we keep a *feature bank* of every real Kaggle training image's feature
vector, plus its class label. Inference uses weighted k-NN voting:

  features = backbone(image)
  sims     = bank @ features                # cosine over L2-normalised feats
  top-K    = k nearest neighbours
  vote     = softmax(sims_top * temp) per neighbour, summed by class

This is a real CNN-feature-based classifier that uses every available training
image rather than collapsing each class to a single mean. It is dramatically
more robust than a single-prototype head when classes are visually diverse.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, List

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as M
import torchvision.transforms as T
from PIL import Image

from datasets import DATASETS
from sample_generator import generate_sample, generate_variants, ensure_all_samples, class_image_paths


IMG_SIZE = 224
DEVICE = torch.device("cpu")
KNN_K = 9               # neighbours considered per query
KNN_TEMP = 24.0         # softmax temperature on similarities


def _build_backbone() -> nn.Module:
    weights = M.MobileNet_V3_Small_Weights.DEFAULT
    m = M.mobilenet_v3_small(weights=weights)
    m.classifier = nn.Identity()
    m.eval()
    for p in m.parameters():
        p.requires_grad_(False)
    return m


_backbone: nn.Module | None = None
_transform: T.Compose | None = None
FEATURE_DIM = 576

# Per-dataset feature bank
_bank: Dict[str, torch.Tensor] = {}        # dataset_id -> [N, 576]
_bank_labels: Dict[str, List[int]] = {}    # dataset_id -> [N] class indices
_class_order: Dict[str, List[str]] = {}    # dataset_id -> ordered class ids
_prototypes: Dict[str, torch.Tensor] = {}  # kept for backward compat (mean per class)


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


def _build_bank(dataset_id: str) -> tuple[torch.Tensor, List[int], List[str], torch.Tensor]:
    ds = DATASETS[dataset_id]
    classes = ds["classes"]
    feats: List[torch.Tensor] = []
    labels: List[int] = []
    proto_means: List[torch.Tensor] = []
    for ci, cls in enumerate(classes):
        # Use up to 25 real images per class for the bank (excluding the 1st = display thumb)
        paths = class_image_paths(dataset_id, cls)[:25]
        if not paths:
            continue
        cls_feats: List[torch.Tensor] = []
        for path in paths:
            with open(path, "rb") as f:
                cls_feats.append(_extract(f.read()))
        for fv in cls_feats:
            feats.append(fv)
            labels.append(ci)
        proto_means.append(F.normalize(torch.stack(cls_feats).mean(0), dim=0))
    bank = torch.stack(feats, dim=0) if feats else torch.zeros(0, FEATURE_DIM)
    proto = torch.stack(proto_means, dim=0) if proto_means else torch.zeros(0, FEATURE_DIM)
    return bank, labels, classes, proto


def warmup() -> None:
    ensure_all_samples()
    _get_backbone()
    for ds_id in DATASETS.keys():
        bank, labels, classes, proto = _build_bank(ds_id)
        _bank[ds_id] = bank
        _bank_labels[ds_id] = labels
        _class_order[ds_id] = classes
        _prototypes[ds_id] = proto


def predict(dataset_id: str, image_bytes: bytes, top_k: int = 3) -> dict:
    if dataset_id not in _bank:
        warmup()
    if dataset_id not in _bank or _bank[dataset_id].shape[0] == 0:
        raise ValueError(f"No feature bank for dataset_id: {dataset_id}")

    bank = _bank[dataset_id]
    labels = _bank_labels[dataset_id]
    classes = _class_order[dataset_id]
    K = len(classes)

    feat = _extract(image_bytes)
    sims_all = (bank @ feat).clamp(-1.0, 1.0)  # [N]

    # Weighted k-NN vote
    k = min(KNN_K, sims_all.shape[0])
    top_sims, top_idx = torch.topk(sims_all, k=k)
    weights = F.softmax(top_sims * KNN_TEMP, dim=0)  # [k]

    class_scores = torch.zeros(K)
    for w, idx in zip(weights, top_idx):
        class_scores[labels[idx.item()]] += w
    # Normalise to probabilities
    class_probs = class_scores / class_scores.sum().clamp_min(1e-9)

    # Per-class peak similarity (used in top-k display)
    peak_sims = torch.full((K,), -1.0)
    for i in range(sims_all.shape[0]):
        c = labels[i]
        if sims_all[i] > peak_sims[c]:
            peak_sims[c] = sims_all[i]

    order = torch.argsort(class_probs, descending=True).tolist()
    top: list[dict] = []
    for idx in order[: max(top_k, 1)]:
        top.append({
            "class_id": classes[idx],
            "label": DATASETS[dataset_id]["class_labels"][classes[idx]],
            "probability": float(class_probs[idx].item()),
            "similarity": float(peak_sims[idx].item()),
        })

    confidence = float(class_probs[order[0]].item())

    return {
        "dataset_id": dataset_id,
        "predicted_class": classes[order[0]],
        "predicted_label": DATASETS[dataset_id]["class_labels"][classes[order[0]]],
        "confidence": confidence,
        "top_k": top,
        "logits": [float(class_probs[i].item()) for i in range(K)],
        "model_arch": f"MobileNetV3-Small (ImageNet, frozen) + weighted k-NN (k={k}, bank={bank.shape[0]})",
    }
