"""End-to-end Kaggle trainer.

For each dataset in TRAIN_JOBS:
  1. Download + unzip from Kaggle  →  /tmp/_train/{dataset_id}
  2. Walk folder structure, build (image_path, label) list per split
  3. Extract 576-D features via frozen MobileNetV3-Small (ImageNet)
  4. Train a small classifier head (Linear→ReLU→Dropout→Linear) on features
  5. Report val accuracy, save state_dict to /app/backend/weights/{dataset_id}.pt
  6. Copy 30 images per class to /app/backend/datasets_real/ for gallery
  7. Delete raw download

Total disk footprint: only weights (~50KB each) + curated gallery (~70MB).
"""
from __future__ import annotations
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as M
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT = Path(__file__).parent
WEIGHTS = ROOT / "weights"
WEIGHTS.mkdir(exist_ok=True)
CURATED = ROOT / "datasets_real"
CURATED.mkdir(exist_ok=True)
TMP = Path("/tmp/_train")
TMP.mkdir(exist_ok=True)
LOG = ROOT / "train.log"


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


# -------- Feature extractor (shared) --------
_backbone = None
_transform = None


def get_backbone():
    global _backbone, _transform
    if _backbone is None:
        w = M.MobileNet_V3_Small_Weights.DEFAULT
        m = M.mobilenet_v3_small(weights=w)
        m.classifier = nn.Identity()
        m.eval()
        for p in m.parameters():
            p.requires_grad_(False)
        _backbone = m
        _transform = w.transforms()
    return _backbone, _transform


@torch.no_grad()
def extract_features(paths: list[Path], batch_size: int = 64) -> torch.Tensor:
    backbone, tf = get_backbone()
    feats = []
    batch = []
    for p in paths:
        try:
            img = Image.open(p).convert("RGB")
            batch.append(tf(img))
        except Exception as e:
            log(f"  skip {p}: {e}")
            batch.append(torch.zeros(3, 224, 224))
        if len(batch) == batch_size:
            x = torch.stack(batch)
            f = backbone(x)
            feats.append(F.normalize(f, dim=1))
            batch = []
    if batch:
        x = torch.stack(batch)
        f = backbone(x)
        feats.append(F.normalize(f, dim=1))
    return torch.cat(feats, dim=0) if feats else torch.zeros(0, 576)


# -------- Head definition --------
class Head(nn.Module):
    def __init__(self, num_classes: int, in_dim: int = 576, hidden: int = 256, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden, num_classes),
        )

    def forward(self, x):
        return self.net(x)


def train_head(train_f: torch.Tensor, train_y: torch.Tensor,
               val_f: torch.Tensor, val_y: torch.Tensor,
               num_classes: int, epochs: int = 80, lr: float = 1e-3,
               weight_decay: float = 5e-4, seed: int = 42) -> tuple[Head, float]:
    torch.manual_seed(seed)
    head = Head(num_classes=num_classes)
    opt = torch.optim.AdamW(head.parameters(), lr=lr, weight_decay=weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    best_val = 0.0
    best_state = None
    bs = 128
    n = train_f.shape[0]
    for ep in range(epochs):
        head.train()
        perm = torch.randperm(n)
        total = 0; correct = 0; loss_sum = 0.0
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            xb = train_f[idx]; yb = train_y[idx]
            logits = head(xb)
            loss = F.cross_entropy(logits, yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
            loss_sum += loss.item() * xb.size(0)
            correct += (logits.argmax(1) == yb).sum().item()
            total += xb.size(0)
        sched.step()
        # Val
        head.eval()
        with torch.no_grad():
            vp = head(val_f).argmax(1)
            vacc = (vp == val_y).float().mean().item()
        if vacc > best_val:
            best_val = vacc
            best_state = {k: v.clone() for k, v in head.state_dict().items()}
        if ep % 10 == 0 or ep == epochs - 1:
            log(f"    ep{ep:>3}: train_loss={loss_sum/total:.4f} train_acc={correct/total:.3f} val_acc={vacc:.3f}  best={best_val:.3f}")
    if best_state is not None:
        head.load_state_dict(best_state)
    return head, best_val


# -------- Dataset jobs --------
# Each job tells us: kaggle slug, how to discover (image_path, class_id) tuples, and the canonical class order.


def discover_brain_mri(root: Path, class_order: list[str]) -> list[tuple[Path, str]]:
    # root/{Training,Testing}/{glioma,meningioma,pituitary,notumor}/*.jpg
    mapping = {"glioma": "glioma", "meningioma": "meningioma",
               "pituitary": "pituitary", "no_tumor": "notumor"}
    items = []
    for split in ["Training", "Testing"]:
        for our_cls, kg_cls in mapping.items():
            d = root / split / kg_cls
            if d.exists():
                for p in d.rglob("*.jpg"):
                    items.append((p, our_cls))
    return items


def discover_lung_ct(root: Path, class_order: list[str]) -> list[tuple[Path, str]]:
    items = []
    for split in ["Data/train", "Data/test", "Data/valid"]:
        base = root / split
        if not base.exists():
            continue
        for d in base.iterdir():
            if not d.is_dir():
                continue
            name = d.name.lower()
            if name.startswith("adenocarcinoma"):
                our = "adenocarcinoma"
            elif name.startswith("large.cell.carcinoma") or name.startswith("large_cell"):
                our = "large_cell"
            elif name.startswith("squamous.cell.carcinoma") or name.startswith("squamous_cell"):
                our = "squamous_cell"
            elif name == "normal":
                our = "normal"
            else:
                continue
            for p in d.rglob("*.*"):
                if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                    items.append((p, our))
    return items


def discover_breast_us(root: Path, class_order: list[str]) -> list[tuple[Path, str]]:
    base = root / "Dataset_BUSI_with_GT"
    items = []
    if not base.exists():
        return items
    for cls in class_order:
        d = base / cls
        if d.exists():
            for p in d.rglob("*.png"):
                if "_mask" in p.name:
                    continue
                items.append((p, cls))
    return items


def discover_kidney_ct(root: Path, class_order: list[str]) -> list[tuple[Path, str]]:
    # Nested twice: CT-KIDNEY.../CT-KIDNEY.../{Normal,Cyst,Stone,Tumor}
    items = []
    for base in root.rglob("CT-KIDNEY-DATASET-Normal-Cyst-Tumor-Stone"):
        if not base.is_dir():
            continue
        for kg_cls in ["Normal", "Cyst", "Stone", "Tumor"]:
            d = base / kg_cls
            if d.exists():
                our = kg_cls.lower()
                for p in d.rglob("*.jpg"):
                    items.append((p, our))
        if items:
            break
    return items


def discover_skin_derm(root: Path, class_order: list[str]) -> list[tuple[Path, str]]:
    items = []
    for split in ["data/train", "data/test", "train", "test"]:
        base = root / split
        if not base.exists():
            continue
        for cls in class_order:
            d = base / cls
            if d.exists():
                for p in d.rglob("*.jpg"):
                    items.append((p, cls))
    return items


TRAIN_JOBS = [
    # (dataset_id, kaggle_slug, class_order, discover_fn, max_per_class_train, max_per_class_val)
    ("breast_us",  "aryashah2k/breast-ultrasound-images-dataset",              ["benign", "malignant", "normal"],                              discover_breast_us,  400, 200),
    ("skin_derm",  "fanconic/skin-cancer-malignant-vs-benign",                 ["benign", "malignant"],                                        discover_skin_derm,  400, 200),
    ("brain_mri",  "masoudnickparvar/brain-tumor-mri-dataset",                 ["glioma", "meningioma", "pituitary", "no_tumor"],              discover_brain_mri,  400, 200),
    ("lung_ct",    "mohamedhanyyy/chest-ctscan-images",                        ["adenocarcinoma", "large_cell", "squamous_cell", "normal"],    discover_lung_ct,    400, 200),
    ("kidney_ct",  "nazmul0087/ct-kidney-dataset-normal-cyst-tumor-and-stone", ["normal", "cyst", "stone", "tumor"],                           discover_kidney_ct,  400, 200),
]


def run_one(dataset_id: str, slug: str, class_order: list[str], discover_fn: Callable,
            max_train: int, max_val: int) -> dict:
    t0 = time.time()
    log(f"=== {dataset_id} START (kaggle: {slug}) ===")
    ds_tmp = TMP / dataset_id
    if ds_tmp.exists():
        shutil.rmtree(ds_tmp)
    ds_tmp.mkdir(parents=True)

    # 1. Download
    log("  downloading…")
    r = subprocess.run(
        ["kaggle", "datasets", "download", "-d", slug, "--unzip", "-p", str(ds_tmp)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        log(f"  ERROR download: {r.stderr[:500]}")
        shutil.rmtree(ds_tmp, ignore_errors=True)
        return {"dataset_id": dataset_id, "status": "download_failed", "error": r.stderr[-300:]}

    # 2. Discover
    items = discover_fn(ds_tmp, class_order)
    log(f"  discovered {len(items)} images")
    if not items:
        shutil.rmtree(ds_tmp, ignore_errors=True)
        return {"dataset_id": dataset_id, "status": "no_images"}

    # Group by class → split train/val deterministically
    cls_to_paths: dict[str, list[Path]] = {c: [] for c in class_order}
    for p, c in items:
        if c in cls_to_paths:
            cls_to_paths[c].append(p)
    for c in cls_to_paths:
        cls_to_paths[c].sort()

    random.seed(42)
    train_items: list[tuple[Path, int]] = []
    val_items: list[tuple[Path, int]] = []
    for ci, c in enumerate(class_order):
        paths = cls_to_paths.get(c, [])
        random.Random(42).shuffle(paths)
        n = len(paths)
        if n == 0:
            log(f"  class '{c}': NO IMAGES"); continue
        if n >= max_train + max_val:
            tr = paths[:max_train]
            va = paths[max_train:max_train + max_val]
        else:
            # 80/20 split for smaller classes
            k = max(1, int(n * 0.8))
            tr = paths[:k]
            va = paths[k:]
        log(f"  class '{c}': train={len(tr)} val={len(va)} (of {n})")
        for p in tr:
            train_items.append((p, ci))
        for p in va:
            val_items.append((p, ci))

    if not train_items or not val_items:
        shutil.rmtree(ds_tmp, ignore_errors=True)
        return {"dataset_id": dataset_id, "status": "insufficient_data"}

    # 3. Extract features
    log(f"  extracting features: {len(train_items)} train + {len(val_items)} val")
    t1 = time.time()
    train_paths = [p for p, _ in train_items]
    train_ys = torch.tensor([y for _, y in train_items], dtype=torch.long)
    val_paths = [p for p, _ in val_items]
    val_ys = torch.tensor([y for _, y in val_items], dtype=torch.long)
    train_f = extract_features(train_paths)
    val_f = extract_features(val_paths)
    log(f"  features done in {time.time() - t1:.1f}s")

    # 4. Train head
    log(f"  training head ({len(class_order)} classes)…")
    head, val_acc = train_head(train_f, train_ys, val_f, val_ys, num_classes=len(class_order), epochs=80)
    log(f"  best val accuracy: {val_acc * 100:.2f}%")

    # 5. Save weights + metadata
    ckpt = WEIGHTS / f"{dataset_id}.pt"
    torch.save({
        "state_dict": head.state_dict(),
        "class_order": class_order,
        "val_acc": val_acc,
        "train_n": len(train_items),
        "val_n": len(val_items),
        "dataset_id": dataset_id,
        "kaggle_slug": slug,
    }, ckpt)
    log(f"  saved weights to {ckpt}")

    # 6. Curate gallery (30 per class)
    curated = CURATED / dataset_id
    if curated.exists():
        shutil.rmtree(curated)
    for c in class_order:
        out_d = curated / c
        out_d.mkdir(parents=True, exist_ok=True)
        paths = cls_to_paths.get(c, [])[:30]
        for i, p in enumerate(paths):
            shutil.copy2(p, out_d / f"{i:03d}{p.suffix.lower()}")

    # 7. Cleanup raw
    shutil.rmtree(ds_tmp, ignore_errors=True)
    log(f"=== {dataset_id} DONE in {time.time() - t0:.1f}s ===\n")
    return {"dataset_id": dataset_id, "status": "ok", "val_acc": val_acc,
            "train_n": len(train_items), "val_n": len(val_items)}


def main():
    # Clean old log
    LOG.write_text("")
    results = []
    for (ds_id, slug, classes, disc, mt, mv) in TRAIN_JOBS:
        try:
            res = run_one(ds_id, slug, classes, disc, mt, mv)
        except Exception as e:
            import traceback
            log(f"FATAL {ds_id}: {e}\n{traceback.format_exc()}")
            res = {"dataset_id": ds_id, "status": "exception", "error": str(e)}
        results.append(res)
        # Write rolling summary
        (WEIGHTS / "summary.json").write_text(json.dumps(results, indent=2))
    log("ALL DONE")
    log(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
