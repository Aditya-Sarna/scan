from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import re
import uuid
import base64
from pathlib import Path
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional, List

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

import datasets as ds_mod
import cnn_model
import sample_generator


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ---------- Models ----------
class AnalyzeRequest(BaseModel):
    image_base64: str
    mime_type: str = "image/jpeg"
    dataset_id: str
    patient_context: Optional[str] = None


class AnalyzeSampleRequest(BaseModel):
    sample_id: str
    patient_context: Optional[str] = None


class TopK(BaseModel):
    class_id: str
    label: str
    probability: float
    similarity: float


class CNNResult(BaseModel):
    dataset_id: str
    predicted_class: str
    predicted_label: str
    confidence: float
    top_k: List[TopK]
    model_arch: str


class DoctorAnalysis(BaseModel):
    summary: str
    observations: List[str]
    key_indicators: List[str]
    recommendations: List[str]
    urgency: str
    differential_notes: Optional[str] = None


class AnalyzeResponse(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    body_part: str
    modality: str
    is_valid_image: bool
    rejection_reason: Optional[str] = None
    cnn: Optional[CNNResult] = None
    abnormal_detected: Optional[bool] = None
    doctor_analysis: Optional[DoctorAnalysis] = None
    timestamp: str


# ---------- LLM helpers ----------
def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("empty response")
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON found in: {text[:200]}")
    return json.loads(match.group(0))


VALIDATE_PROMPT_TEMPLATE = """You are a strict image-type validator for a medical imaging tool.

The user is using the "{dataset_name}" pipeline ({modality} of the {body_part}).
This pipeline only accepts: {accepted_description}.

Decide whether the uploaded image plausibly fits that description.
Reject anything else (random photos, paper/text, art, screenshots, scans of other body parts or other modalities, blank images).

Return STRICTLY this JSON, nothing else:
{{
  "is_valid": boolean,
  "reason": string  // 1 sentence
}}
"""


REPORT_PROMPT_TEMPLATE = """You are a senior board-certified radiologist writing a draft mini-report.

Pipeline: {dataset_name} ({modality} · {body_part}).
A small CNN classifier produced this verdict on the attached image:

  Predicted class: {predicted_label}
  Confidence: {confidence:.2f}
  Top-3:
{topk_block}

The image is attached. Use it together with the CNN verdict to write a structured report.
You may agree, hedge, or note the CNN may be wrong if the image clearly disagrees.
{patient_block}

Return STRICTLY valid JSON, no prose outside JSON:
{{
  "summary": string,            // 2-4 sentences, patient-readable
  "observations": [string],     // 3-5 technical/anatomical bullets
  "key_indicators": [string],   // 2-4 imaging signs that support or challenge the CNN verdict
  "recommendations": [string],  // 3-4 next-step recommendations
  "urgency": "low" | "moderate" | "high" | "critical",
  "differential_notes": string  // 1 sentence on alternative diagnoses
}}
"""


async def _claude_chat(system: str) -> LlmChat:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "LLM key not configured")
    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"mri-{uuid.uuid4()}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")


async def validate_image(dataset: dict, image_b64: str) -> dict:
    sys_p = "You validate medical-imaging uploads. Output JSON only."
    user_p = VALIDATE_PROMPT_TEMPLATE.format(
        dataset_name=dataset["name"],
        modality=dataset["modality"],
        body_part=dataset["body_part"],
        accepted_description=dataset["accepted_description"],
    )
    chat = await _claude_chat(sys_p)
    msg = UserMessage(text=user_p, file_contents=[ImageContent(image_base64=image_b64)])
    raw = await chat.send_message(msg)
    return _extract_json(str(raw))


async def doctor_report(dataset: dict, cnn: dict, image_b64: str, patient_context: Optional[str]) -> dict:
    topk_block = "\n".join(
        [f"  - {t['label']}: prob={t['probability']:.2f}, sim={t['similarity']:.2f}" for t in cnn["top_k"]]
    )
    patient_block = ""
    if patient_context:
        patient_block = f"\nPatient context provided by user: {patient_context.strip()[:500]}"
    sys_p = "You write structured radiology mini-reports. Output strict JSON only."
    user_p = REPORT_PROMPT_TEMPLATE.format(
        dataset_name=dataset["name"],
        modality=dataset["modality"],
        body_part=dataset["body_part"],
        predicted_label=cnn["predicted_label"],
        confidence=cnn["confidence"],
        topk_block=topk_block,
        patient_block=patient_block,
    )
    chat = await _claude_chat(sys_p)
    msg = UserMessage(text=user_p, file_contents=[ImageContent(image_base64=image_b64)])
    raw = await chat.send_message(msg)
    return _extract_json(str(raw))


# ---------- Helpers ----------
def _parse_b64(image_b64: str) -> bytes:
    b = image_b64
    if "," in b and b.strip().startswith("data:"):
        b = b.split(",", 1)[1]
    try:
        return base64.b64decode(b)
    except Exception as e:
        raise HTTPException(400, f"Invalid base64 image: {e}")


def _normal_class(dataset: dict, predicted_class: str) -> bool:
    """Return True if the predicted class is the 'normal/no-finding' class."""
    benign_set = {"no_tumor", "normal", "benign"}
    return predicted_class in benign_set


def _doctor_obj(d: Optional[dict]) -> Optional[DoctorAnalysis]:
    if not d:
        return None
    try:
        return DoctorAnalysis(
            summary=str(d.get("summary", "")),
            observations=[str(x) for x in (d.get("observations") or [])][:8],
            key_indicators=[str(x) for x in (d.get("key_indicators") or [])][:8],
            recommendations=[str(x) for x in (d.get("recommendations") or [])][:8],
            urgency=str(d.get("urgency") or "low"),
            differential_notes=d.get("differential_notes"),
        )
    except Exception as e:
        logger.warning(f"doctor parse fail: {e}")
        return None


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"message": "Multi-Cancer CNN Analyzer", "status": "ok", "datasets": len(ds_mod.DATASETS)}


@api_router.get("/dataset-status")
async def dataset_status():
    """Per-(dataset, class) real-image counts pulled from Kaggle datasets."""
    return {"counts": sample_generator.dataset_status()}


KAGGLE_SOURCES = {
    "brain_mri": "masoudnickparvar/brain-tumor-mri-dataset",
    "lung_ct": "mohamedhanyyy/chest-ctscan-images",
    "breast_us": "aryashah2k/breast-ultrasound-images-dataset",
    "skin_derm": "fanconic/skin-cancer-malignant-vs-benign",
    "kidney_ct": "nazmul0087/ct-kidney-dataset-normal-cyst-tumor-and-stone",
}


@api_router.get("/datasets")
async def datasets_list():
    out = []
    counts = sample_generator.dataset_status()
    for d in ds_mod.list_datasets():
        d2 = dict(d)
        d2["kaggle_source"] = KAGGLE_SOURCES.get(d["id"])
        d2["sample_counts"] = counts.get(d["id"], {})
        d2["samples"] = [
            {**s, "image_url": f"/api/sample-image/{s['id']}"}
            for s in sample_generator.list_samples_for(d["id"])
        ]
        out.append(d2)
    return {"datasets": out}


@api_router.get("/sample-image/{sample_id}")
async def sample_image(sample_id: str):
    p = sample_generator.get_sample_path(sample_id)
    if not p:
        raise HTTPException(404, "sample not found")
    suffix = p.suffix.lower()
    media = "image/png" if suffix == ".png" else "image/jpeg"
    return FileResponse(str(p), media_type=media)


async def _run_pipeline(dataset_id: str, image_bytes: bytes, image_b64: str, patient_context: Optional[str], skip_validation: bool = False) -> AnalyzeResponse:
    dataset = ds_mod.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(400, f"Unknown dataset_id: {dataset_id}")

    # Step 1 — vision validation (skipped for trusted samples)
    is_valid = True
    rejection_reason = None
    if not skip_validation:
        try:
            v = await validate_image(dataset, image_b64)
        except Exception as e:
            logger.exception("Validate failed")
            raise HTTPException(502, f"Validation failed: {e}")
        is_valid = bool(v.get("is_valid"))
        rejection_reason = v.get("reason") if not is_valid else None

    cnn_obj = None
    abnormal = None
    doctor_obj = None

    # Step 2 — CNN classification
    if is_valid:
        try:
            cnn_raw = cnn_model.predict(dataset_id, image_bytes, top_k=3)
        except Exception as e:
            logger.exception("CNN failed")
            raise HTTPException(500, f"CNN inference failed: {e}")
        cnn_obj = CNNResult(**cnn_raw)
        abnormal = not _normal_class(dataset, cnn_raw["predicted_class"])

        # Step 3 — Claude doctor report
        try:
            d = await doctor_report(dataset, cnn_raw, image_b64, patient_context)
            doctor_obj = _doctor_obj(d)
        except Exception as e:
            logger.warning(f"Doctor report failed: {e}")

    response = AnalyzeResponse(
        id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        dataset_name=dataset["name"],
        body_part=dataset["body_part"],
        modality=dataset["modality"],
        is_valid_image=is_valid,
        rejection_reason=rejection_reason,
        cnn=cnn_obj,
        abnormal_detected=abnormal,
        doctor_analysis=doctor_obj,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    try:
        await db.analyses.insert_one(response.model_dump())
    except Exception as e:
        logger.warning(f"persist fail: {e}")

    return response


@api_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    if req.dataset_id not in ds_mod.DATASETS:
        raise HTTPException(400, f"Unknown dataset_id: {req.dataset_id}")

    image_bytes = _parse_b64(req.image_base64)
    if len(image_bytes) < 200:
        raise HTTPException(400, "Image payload too small")
    if len(image_bytes) > 12 * 1024 * 1024:
        raise HTTPException(400, "Image too large (max 12MB)")

    image_b64 = base64.b64encode(image_bytes).decode()
    return await _run_pipeline(req.dataset_id, image_bytes, image_b64, req.patient_context, skip_validation=False)


@api_router.post("/analyze-sample", response_model=AnalyzeResponse)
async def analyze_sample(req: AnalyzeSampleRequest):
    parts = req.sample_id.split("__")
    if len(parts) < 2:
        raise HTTPException(400, "Bad sample_id")
    dataset_id = parts[0]
    p = sample_generator.get_sample_path(req.sample_id)
    if not p:
        raise HTTPException(404, "sample not found")
    image_bytes = p.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode()
    return await _run_pipeline(dataset_id, image_bytes, image_b64, req.patient_context, skip_validation=True)


@api_router.get("/history")
async def history(limit: int = 20):
    items = await db.analyses.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"items": items}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    sample_generator.ensure_all_samples()
    cnn_model.warmup()
    logger.info(f"CNN warm: {len(ds_mod.DATASETS)} datasets ready")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
