# NEURO-CNN — Multi-cancer Image Analyzer (PRD)

## Problem statement
Build a web app that takes medical images across body parts (brain MRI, lung CT, breast ultrasound, skin dermoscopy, kidney CT), verifies the image type, runs a real trained CNN classification, and drafts a doctor-style radiology report. All classification must be CNN-based, trained on real Kaggle datasets.

## Architecture
- FastAPI backend (Python 3.11) + MongoDB
- React + Tailwind + Shadcn frontend
- **Classifier**: MobileNetV3-Small (ImageNet pretrained, frozen) + dataset-specific MLP head trained on each Kaggle dataset
- **Validator**: Claude Sonnet 4.5 vision (rejects non-matching images)
- **Reporter**: Claude Sonnet 4.5 generates structured doctor-style report given the CNN's verdict

## Datasets (Kaggle)
| Dataset | Slug | Classes | Train N | Val Acc |
|---|---|---|---|---|
| brain_mri | masoudnickparvar/brain-tumor-mri-dataset | 4 | 1600 | 87.8% |
| lung_ct | mohamedhanyyy/chest-ctscan-images | 4 | 799 | 78.1% |
| breast_us | aryashah2k/breast-ultrasound-images-dataset | 3 | 743 | 100% |
| skin_derm | fanconic/skin-cancer-malignant-vs-benign | 2 | 800 | 87.5% |
| kidney_ct | nazmul0087/ct-kidney-dataset-normal-cyst-tumor-and-stone | 4 | 1600 | 91.5% |

## Endpoints
- GET /api/datasets — dataset list + train_info + sample_counts + kaggle_source
- GET /api/sample-image/{id} — serves real Kaggle thumbnail
- GET /api/dataset-status — per-class image counts on disk
- POST /api/analyze {image_base64, dataset_id, patient_context} — full pipeline (validate → CNN → report)
- POST /api/analyze-sample {sample_id, patient_context} — trusted samples, skip validation
- GET /api/history

## What's been implemented
- [2026-02] Full stack MVP with brain MRI
- [2026-02] 5 datasets, sample gallery with backend-proxied images
- [2026-02] Trained CNN heads on real Kaggle data; `/app/backend/weights/*.pt` + summary.json
- [2026-02] Confidence distribution properly spreads (37-99% range, 23% stdev)

## Backlog
- P1: Per-dataset held-out test set accuracy surface on UI
- P1: Multi-class skin (HAM10000) once disk allows
- P2: Allow uploading custom .pth weights to override
- P2: Treatment plan generation beyond the report

## Current status
All 5 datasets trained. Gallery works. Confidence is varied. Accuracy on held-out Kaggle val splits: 78-100%.
