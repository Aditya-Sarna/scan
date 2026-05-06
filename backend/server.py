from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
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
from pydantic import BaseModel, Field
from typing import Optional, List

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
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
    patient_context: Optional[str] = None  # optional symptoms / age / context


class DoctorAnalysis(BaseModel):
    summary: str
    observations: List[str]
    key_indicators: List[str]
    recommendations: List[str]
    urgency: str  # low | moderate | high | critical
    differential_notes: Optional[str] = None


class AnalyzeResponse(BaseModel):
    id: str
    is_mri: bool
    rejection_reason: Optional[str] = None
    classification: Optional[str] = None  # glioma | meningioma | pituitary | no_tumor
    classification_label: Optional[str] = None  # human readable
    confidence: Optional[float] = None
    tumor_detected: Optional[bool] = None
    doctor_analysis: Optional[DoctorAnalysis] = None
    timestamp: str


# ---------- Sample Gallery ----------
SAMPLE_GALLERY = [
    {
        "id": "sample-glioma",
        "label": "Glioma",
        "category": "glioma",
        "url": "https://prod.smc.edu/_resources/images/news/2018/2018-09-27-mri-brain-imaging.jpg",
        "description": "Axial T1 with contrast — suggestive of glioma",
    },
    {
        "id": "sample-meningioma",
        "label": "Meningioma",
        "category": "meningioma",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/MRI_meningioma_-_RIGHT_temporal_FLAIR_axial.jpg/640px-MRI_meningioma_-_RIGHT_temporal_FLAIR_axial.jpg",
        "description": "FLAIR axial — meningioma reference",
    },
    {
        "id": "sample-pituitary",
        "label": "Pituitary",
        "category": "pituitary",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Pituitary_macroadenoma_with_hemorrhage.jpg/640px-Pituitary_macroadenoma_with_hemorrhage.jpg",
        "description": "Sagittal — pituitary region reference",
    },
    {
        "id": "sample-normal",
        "label": "Normal",
        "category": "no_tumor",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/MRI_brain_sagittal_section.jpg/640px-MRI_brain_sagittal_section.jpg",
        "description": "Healthy brain MRI reference",
    },
]


CLASS_LABELS = {
    "glioma": "Glioma Tumor",
    "meningioma": "Meningioma Tumor",
    "pituitary": "Pituitary Tumor",
    "no_tumor": "No Tumor",
}


# ---------- Helpers ----------
def _extract_json(text: str) -> dict:
    """Extract first JSON object from a string (handles ```json fences)."""
    if not text:
        raise ValueError("empty response")
    # remove code fences
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    # find first { ... } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON found in: {text[:200]}")
    return json.loads(match.group(0))


SYSTEM_PROMPT = """You are a senior board-certified neuroradiologist reviewing a single uploaded image.

Your task has two stages:

STAGE 1 — VALIDATION
Decide whether the image is a real brain MRI scan (axial, coronal, or sagittal slice).
- If the image is NOT a brain MRI (e.g., a photograph, paper document, screenshot, X-ray of another body part, CT scan, art, blank image, hand-drawn sketch), set "is_mri": false and explain briefly in "rejection_reason".
- Only mark is_mri:true if the image clearly shows brain anatomy in a typical MRI grayscale slice.

STAGE 2 — ANALYSIS (only when is_mri:true)
Classify into exactly one of:
  "glioma"     — diffuse infiltrative intra-axial mass, often hyperintense on FLAIR/T2
  "meningioma" — extra-axial dural-based, well-circumscribed, may show dural tail
  "pituitary"  — sellar/parasellar region mass involving the pituitary fossa
  "no_tumor"   — healthy brain parenchyma, no mass effect

Provide your "doctor_analysis" as a structured medical mini-report.
- summary: one short paragraph (2-4 sentences) explaining what you see, written for a patient
- observations: 3-5 bullet observations (technical, anatomical)
- key_indicators: 2-4 specific imaging signs you used to reach the classification
- recommendations: 3-4 clear next-step recommendations (further imaging, specialist referral, follow-up timeline, lifestyle)
- urgency: one of "low" | "moderate" | "high" | "critical"
- differential_notes: one sentence on possible alternative diagnoses to consider

Confidence must be a float in [0.50, 0.99]. Be honest — if image quality is poor, lower the confidence.

Return STRICTLY valid JSON, no prose outside JSON, with this exact schema:

{
  "is_mri": boolean,
  "rejection_reason": string | null,
  "classification": "glioma" | "meningioma" | "pituitary" | "no_tumor" | null,
  "confidence": number | null,
  "doctor_analysis": {
    "summary": string,
    "observations": [string],
    "key_indicators": [string],
    "recommendations": [string],
    "urgency": "low" | "moderate" | "high" | "critical",
    "differential_notes": string
  } | null
}
"""


async def analyze_with_claude(image_bytes: bytes, mime_type: str, patient_context: Optional[str]) -> dict:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "LLM key not configured")

    image_b64 = base64.b64encode(image_bytes).decode()

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"mri-{uuid.uuid4()}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    ctx_text = (
        "Analyze the attached image per the protocol. "
        "Return ONLY the JSON object, no markdown, no commentary."
    )
    if patient_context:
        ctx_text += f"\n\nPatient context provided by user: {patient_context.strip()[:500]}"

    image_content = ImageContent(image_base64=image_b64)
    message = UserMessage(text=ctx_text, file_contents=[image_content])

    raw = await chat.send_message(message)
    logger.info(f"Claude raw (truncated): {str(raw)[:300]}")

    if isinstance(raw, dict):
        return raw
    return _extract_json(str(raw))


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"message": "Neuro MRI Analyzer API", "status": "ok"}


@api_router.get("/sample-gallery")
async def sample_gallery():
    return {"samples": SAMPLE_GALLERY}


@api_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    # Decode base64
    try:
        b64 = req.image_base64
        if "," in b64 and b64.strip().startswith("data:"):
            b64 = b64.split(",", 1)[1]
        image_bytes = base64.b64decode(b64)
    except Exception as e:
        raise HTTPException(400, f"Invalid base64 image: {e}")

    if len(image_bytes) < 200:
        raise HTTPException(400, "Image payload too small")
    if len(image_bytes) > 12 * 1024 * 1024:
        raise HTTPException(400, "Image too large (max 12MB)")

    mime = req.mime_type or "image/jpeg"
    if mime not in ("image/jpeg", "image/png", "image/webp", "image/jpg"):
        mime = "image/jpeg"

    try:
        parsed = await analyze_with_claude(image_bytes, mime, req.patient_context)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("LLM analysis failed")
        raise HTTPException(502, f"Analysis service failed: {e}")

    is_mri = bool(parsed.get("is_mri"))
    classification = parsed.get("classification") if is_mri else None
    confidence = parsed.get("confidence") if is_mri else None

    if classification and classification not in CLASS_LABELS:
        classification = None

    doctor = parsed.get("doctor_analysis")
    doctor_obj = None
    if is_mri and doctor:
        try:
            doctor_obj = DoctorAnalysis(
                summary=str(doctor.get("summary", "")),
                observations=[str(x) for x in (doctor.get("observations") or [])][:8],
                key_indicators=[str(x) for x in (doctor.get("key_indicators") or [])][:8],
                recommendations=[str(x) for x in (doctor.get("recommendations") or [])][:8],
                urgency=str(doctor.get("urgency") or "low"),
                differential_notes=doctor.get("differential_notes"),
            )
        except Exception as e:
            logger.warning(f"doctor parse fail: {e}")

    response = AnalyzeResponse(
        id=str(uuid.uuid4()),
        is_mri=is_mri,
        rejection_reason=(parsed.get("rejection_reason") if not is_mri else None),
        classification=classification,
        classification_label=CLASS_LABELS.get(classification) if classification else None,
        confidence=confidence,
        tumor_detected=(classification is not None and classification != "no_tumor"),
        doctor_analysis=doctor_obj,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Persist (no _id leaks, datetime as string)
    try:
        doc = response.model_dump()
        await db.analyses.insert_one(doc)
    except Exception as e:
        logger.warning(f"persist fail: {e}")

    return response


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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
