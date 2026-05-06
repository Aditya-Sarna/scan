"""Synthetic sample image generator.

Creates visually-distinct PNG samples for each (dataset, class) so:
1) The frontend gallery has reliable images served from the backend (no CORS).
2) The CNN can build meaningful class prototypes by processing real-pixel images.

The synthetic look is intentionally simple but varies across classes so the
CNN's feature vectors differ — giving deterministic, class-conditional predictions
on sample images and on user uploads of similar visual character.
"""
from __future__ import annotations

import os
import random
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

from datasets import DATASETS

SAMPLE_DIR = Path(__file__).parent / "sample_images"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

CANVAS = 384


def _seed_for(dataset_id: str, class_id: str) -> int:
    return abs(hash(f"{dataset_id}::{class_id}")) % (2**31)


# ---------- Per-dataset drawing primitives ----------

def _draw_brain(draw: ImageDraw.ImageDraw, rng: random.Random, class_id: str):
    # grayscale axial brain look
    draw.rectangle((0, 0, CANVAS, CANVAS), fill=(8, 8, 8))
    # outer skull + parenchyma
    draw.ellipse((40, 50, CANVAS - 40, CANVAS - 30), fill=(190, 190, 190))
    draw.ellipse((58, 70, CANVAS - 58, CANVAS - 50), fill=(120, 120, 120))
    # gyri lines
    for _ in range(60):
        x, y = rng.randint(70, CANVAS - 70), rng.randint(80, CANVAS - 60)
        r = rng.randint(2, 8)
        v = rng.randint(70, 200)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(v, v, v))

    # class-specific lesion
    if class_id == "glioma":
        cx, cy = rng.randint(120, 200), rng.randint(140, 220)
        draw.ellipse((cx - 35, cy - 28, cx + 35, cy + 28), fill=(220, 220, 220))
        draw.ellipse((cx - 18, cy - 14, cx + 18, cy + 14), fill=(80, 80, 80))
    elif class_id == "meningioma":
        cx, cy = rng.randint(80, 110), rng.randint(140, 200)
        draw.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(240, 240, 240))
    elif class_id == "pituitary":
        cx, cy = CANVAS // 2, CANVAS - 110
        draw.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(230, 230, 230))
    # no_tumor: nothing extra


def _draw_lung(draw: ImageDraw.ImageDraw, rng: random.Random, class_id: str):
    draw.rectangle((0, 0, CANVAS, CANVAS), fill=(20, 20, 20))
    # body outline
    draw.ellipse((20, 60, CANVAS - 20, CANVAS - 20), fill=(150, 150, 150))
    # heart
    draw.ellipse((CANVAS // 2 - 28, 130, CANVAS // 2 + 28, 200), fill=(110, 110, 110))
    # lungs (dark)
    draw.ellipse((50, 100, 170, 280), fill=(35, 35, 35))
    draw.ellipse((CANVAS - 170, 100, CANVAS - 50, 280), fill=(35, 35, 35))
    # vessels
    for _ in range(40):
        x = rng.choice([rng.randint(60, 160), rng.randint(CANVAS - 160, CANVAS - 60)])
        y = rng.randint(110, 270)
        r = rng.randint(2, 5)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(170, 170, 170))

    # nodule placement
    side = rng.choice(["L", "R"])
    cx = rng.randint(70, 150) if side == "L" else rng.randint(CANVAS - 150, CANVAS - 70)
    cy = rng.randint(140, 240)
    if class_id == "adenocarcinoma":
        draw.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(220, 220, 220))
    elif class_id == "large_cell":
        draw.ellipse((cx - 22, cy - 18, cx + 22, cy + 18), fill=(230, 230, 230))
    elif class_id == "squamous_cell":
        # central, near hilum
        draw.ellipse((CANVAS // 2 - 24, 200, CANVAS // 2 + 24, 248), fill=(225, 225, 225))


def _draw_breast(draw: ImageDraw.ImageDraw, rng: random.Random, class_id: str):
    draw.rectangle((0, 0, CANVAS, CANVAS), fill=(0, 0, 0))
    # ultrasound fan
    pts = [(CANVAS // 2, 0), (40, CANVAS), (CANVAS - 40, CANVAS)]
    draw.polygon(pts, fill=(70, 70, 70))
    # texture lines
    for _ in range(140):
        x = rng.randint(60, CANVAS - 60)
        y = rng.randint(80, CANVAS - 40)
        v = rng.randint(40, 140)
        draw.point((x, y), fill=(v, v, v))
    # lesion
    if class_id == "benign":
        cx, cy = CANVAS // 2 - 20, 200
        draw.ellipse((cx - 28, cy - 18, cx + 28, cy + 18), fill=(20, 20, 20))
    elif class_id == "malignant":
        cx, cy = CANVAS // 2 + 10, 220
        # irregular
        for ang in range(0, 360, 25):
            r = rng.randint(18, 36)
            x = cx + r * math.cos(math.radians(ang))
            y = cy + r * math.sin(math.radians(ang))
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(15, 15, 15))


def _draw_skin(draw: ImageDraw.ImageDraw, rng: random.Random, class_id: str):
    # skin background
    draw.rectangle((0, 0, CANVAS, CANVAS), fill=(220, 180, 155))
    # add pores / texture
    for _ in range(800):
        x, y = rng.randint(0, CANVAS), rng.randint(0, CANVAS)
        draw.point((x, y), fill=(rng.randint(160, 230), rng.randint(130, 180), rng.randint(110, 160)))
    cx, cy = CANVAS // 2 + rng.randint(-30, 30), CANVAS // 2 + rng.randint(-30, 30)
    if class_id == "melanoma":
        # asymmetric, dark, multi-color
        for ang in range(0, 360, 18):
            r = rng.randint(60, 110)
            x = cx + r * math.cos(math.radians(ang))
            y = cy + r * math.sin(math.radians(ang))
            shade = rng.choice([(20, 10, 8), (60, 20, 10), (85, 40, 20)])
            draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill=shade)
        draw.ellipse((cx - 50, cy - 40, cx + 50, cy + 40), fill=(30, 15, 8))
    elif class_id == "nevus":
        draw.ellipse((cx - 60, cy - 60, cx + 60, cy + 60), fill=(90, 50, 25))
    elif class_id == "basal_cell":
        # pearly + telangiectasia
        draw.ellipse((cx - 70, cy - 50, cx + 70, cy + 50), fill=(210, 170, 150))
        for _ in range(20):
            x1 = cx + rng.randint(-50, 50)
            y1 = cy + rng.randint(-30, 30)
            x2 = x1 + rng.randint(-25, 25)
            y2 = y1 + rng.randint(-25, 25)
            draw.line((x1, y1, x2, y2), fill=(200, 50, 50), width=2)


def _draw_kidney(draw: ImageDraw.ImageDraw, rng: random.Random, class_id: str):
    draw.rectangle((0, 0, CANVAS, CANVAS), fill=(15, 15, 15))
    # abdomen outline
    draw.ellipse((30, 40, CANVAS - 30, CANVAS - 20), fill=(140, 140, 140))
    # spine
    draw.ellipse((CANVAS // 2 - 20, CANVAS - 110, CANVAS // 2 + 20, CANVAS - 70), fill=(220, 220, 220))
    # kidneys
    for cx in [120, CANVAS - 120]:
        cy = 200
        draw.ellipse((cx - 36, cy - 50, cx + 36, cy + 50), fill=(80, 80, 80))

    if class_id == "cyst":
        draw.ellipse((CANVAS - 150, 180, CANVAS - 110, 230), fill=(40, 40, 40))
    elif class_id == "stone":
        for _ in range(3):
            x = rng.randint(110, 130)
            y = rng.randint(170, 230)
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255))
    elif class_id == "tumor":
        cx, cy = 120, 180
        draw.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(210, 210, 210))


DRAWERS = {
    "brain_mri": _draw_brain,
    "lung_ct": _draw_lung,
    "breast_us": _draw_breast,
    "skin_derm": _draw_skin,
    "kidney_ct": _draw_kidney,
}


def generate_sample(dataset_id: str, class_id: str) -> Path:
    sample_id = f"{dataset_id}__{class_id}"
    out = SAMPLE_DIR / f"{sample_id}.jpg"
    if out.exists():
        return out
    rng = random.Random(_seed_for(dataset_id, class_id))
    img = Image.new("RGB", (CANVAS, CANVAS), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    DRAWERS[dataset_id](draw, rng, class_id)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    img.save(out, "JPEG", quality=88)
    return out


def ensure_all_samples():
    """Generate every dataset × class sample if missing."""
    paths = []
    for ds in DATASETS.values():
        for cls in ds["classes"]:
            paths.append((ds["id"], cls, generate_sample(ds["id"], cls)))
    return paths


def get_sample_path(sample_id: str) -> Path | None:
    p = SAMPLE_DIR / f"{sample_id}.jpg"
    return p if p.exists() else None


def list_samples_for(dataset_id: str):
    ds = DATASETS.get(dataset_id)
    if not ds:
        return []
    out = []
    for cls in ds["classes"]:
        sample_id = f"{dataset_id}__{cls}"
        out.append({
            "id": sample_id,
            "dataset_id": dataset_id,
            "class_id": cls,
            "label": ds["class_labels"][cls],
        })
    return out
