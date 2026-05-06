"""Real Kaggle dataset image loader.

Reads from /app/backend/datasets_real/{dataset_id}/{class_id}/*.jpg

Provides:
- A "display" sample per class (used in the gallery thumbnail and on /api/sample-image/{id})
- A list of N images per class used to build robust CNN prototypes

Source datasets (Kaggle):
  brain_mri  → masoudnickparvar/brain-tumor-mri-dataset
  lung_ct    → mohamedhanyyy/chest-ctscan-images
  breast_us  → aryashah2k/breast-ultrasound-images-dataset
  skin_derm  → fanconic/skin-cancer-malignant-vs-benign
  kidney_ct  → nazmul0087/ct-kidney-dataset-normal-cyst-tumor-and-stone
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from datasets import DATASETS

REAL_DIR = Path(__file__).parent / "datasets_real"
SAMPLE_DIR = Path(__file__).parent / "sample_images"  # symlink-style: copies of display thumbs
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

# Cache: dataset_id -> class_id -> sorted list[Path]
_INDEX: dict[str, dict[str, list[Path]]] = {}


def _scan() -> None:
    """Build / refresh the index of real images."""
    global _INDEX
    _INDEX = {}
    for ds_id, ds in DATASETS.items():
        cls_map = {}
        for cls in ds["classes"]:
            d = REAL_DIR / ds_id / cls
            if d.exists():
                files = sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
            else:
                files = []
            cls_map[cls] = files
        _INDEX[ds_id] = cls_map


def _ensure_indexed() -> None:
    if not _INDEX:
        _scan()


def class_image_paths(dataset_id: str, class_id: str) -> List[Path]:
    _ensure_indexed()
    return _INDEX.get(dataset_id, {}).get(class_id, [])


def display_path(dataset_id: str, class_id: str) -> Path | None:
    """The image we render in the gallery thumbnail. First file in class folder."""
    files = class_image_paths(dataset_id, class_id)
    return files[0] if files else None


def ensure_all_samples() -> None:
    """No-op kept for compatibility — real images already on disk."""
    _ensure_indexed()


def generate_sample(dataset_id: str, class_id: str) -> Path:
    """Returns the display path for a class. Required for /api/sample-image/{id} resolution."""
    p = display_path(dataset_id, class_id)
    if p is None:
        raise FileNotFoundError(f"No real images for {dataset_id}/{class_id}")
    return p


def generate_variants(dataset_id: str, class_id: str, n: int = 8) -> List[Path]:
    """Returns up to n additional real images for prototype building (after display image)."""
    files = class_image_paths(dataset_id, class_id)
    return files[1 : 1 + n]  # skip the display image


def get_sample_path(sample_id: str) -> Path | None:
    """Resolves /api/sample-image/{sample_id} to a real file. sample_id = '{dataset}__{class}' or '{dataset}__{class}__{idx}'."""
    parts = sample_id.split("__")
    if len(parts) < 2:
        return None
    ds_id, cls = parts[0], parts[1]
    files = class_image_paths(ds_id, cls)
    if not files:
        return None
    if len(parts) == 2:
        return files[0]
    # '__N' to access a specific index in the class folder
    try:
        idx = int(parts[2])
    except ValueError:
        return None
    if 0 <= idx < len(files):
        return files[idx]
    return None


def list_samples_for(dataset_id: str) -> list[dict]:
    _ensure_indexed()
    ds = DATASETS.get(dataset_id)
    if not ds:
        return []
    out = []
    for cls in ds["classes"]:
        files = class_image_paths(dataset_id, cls)
        if not files:
            continue
        sample_id = f"{dataset_id}__{cls}"
        out.append({
            "id": sample_id,
            "dataset_id": dataset_id,
            "class_id": cls,
            "label": ds["class_labels"][cls],
            "source_count": len(files),
        })
    return out


def dataset_status() -> dict:
    """Counts of real images available per (dataset, class)."""
    _ensure_indexed()
    out = {}
    for ds_id, classes in _INDEX.items():
        out[ds_id] = {cls: len(files) for cls, files in classes.items()}
    return out
