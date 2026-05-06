"""Catalog of medical imaging datasets across body parts.

Each dataset defines:
- id, name, body_part, modality
- classes (model labels) and human-readable class_labels
- accepted_description (used in vision-validation prompt)
- sample_seed (for synthetic sample generation)
"""

DATASETS = {
    "brain_mri": {
        "id": "brain_mri",
        "name": "Brain Tumor MRI",
        "body_part": "Brain",
        "modality": "MRI",
        "tagline": "Glioma · Meningioma · Pituitary · Normal",
        "classes": ["glioma", "meningioma", "pituitary", "no_tumor"],
        "class_labels": {
            "glioma": "Glioma",
            "meningioma": "Meningioma",
            "pituitary": "Pituitary Tumor",
            "no_tumor": "No Tumor",
        },
        "accepted_description": "an axial / coronal / sagittal brain MRI slice (T1, T2 or FLAIR, grayscale)",
    },
    "lung_ct": {
        "id": "lung_ct",
        "name": "Lung Cancer CT",
        "body_part": "Lung",
        "modality": "CT",
        "tagline": "Adenocarcinoma · Large Cell · Squamous Cell · Normal",
        "classes": ["adenocarcinoma", "large_cell", "squamous_cell", "normal"],
        "class_labels": {
            "adenocarcinoma": "Adenocarcinoma",
            "large_cell": "Large Cell Carcinoma",
            "squamous_cell": "Squamous Cell Carcinoma",
            "normal": "Normal Lung",
        },
        "accepted_description": "an axial chest / thoracic CT slice showing lung parenchyma",
    },
    "breast_us": {
        "id": "breast_us",
        "name": "Breast Ultrasound",
        "body_part": "Breast",
        "modality": "Ultrasound",
        "tagline": "Benign · Malignant · Normal",
        "classes": ["benign", "malignant", "normal"],
        "class_labels": {
            "benign": "Benign Lesion",
            "malignant": "Malignant Tumor",
            "normal": "Normal Tissue",
        },
        "accepted_description": "a breast ultrasound scan (grayscale fan-shaped sonogram)",
    },
    "skin_derm": {
        "id": "skin_derm",
        "name": "Skin Lesion Dermoscopy",
        "body_part": "Skin",
        "modality": "Dermoscopy",
        "tagline": "Benign · Malignant",
        "classes": ["benign", "malignant"],
        "class_labels": {
            "benign": "Benign Lesion",
            "malignant": "Malignant Melanoma",
        },
        "accepted_description": "a close-up dermoscopic image of a skin lesion or mole",
    },
    "kidney_ct": {
        "id": "kidney_ct",
        "name": "Kidney CT",
        "body_part": "Kidney",
        "modality": "CT",
        "tagline": "Normal · Cyst · Stone · Tumor",
        "classes": ["normal", "cyst", "stone", "tumor"],
        "class_labels": {
            "normal": "Normal Kidney",
            "cyst": "Renal Cyst",
            "stone": "Kidney Stone",
            "tumor": "Renal Tumor",
        },
        "accepted_description": "an axial abdominal CT slice showing the kidneys",
    },
}


def list_datasets():
    return [
        {
            "id": d["id"],
            "name": d["name"],
            "body_part": d["body_part"],
            "modality": d["modality"],
            "tagline": d["tagline"],
            "classes": d["classes"],
            "class_labels": d["class_labels"],
        }
        for d in DATASETS.values()
    ]


def get_dataset(dataset_id: str):
    return DATASETS.get(dataset_id)
