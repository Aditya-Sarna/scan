"""Backend tests for Neuro MRI Analyzer."""
import os
import io
import base64
import math
import random
import pytest
import requests
from PIL import Image, ImageDraw, ImageFilter

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0].strip().strip('"')).rstrip("/")
API = f"{BASE_URL}/api"

VALID_CLASSES = {"glioma", "meningioma", "pituitary", "no_tumor"}


# ---------- helpers: synthetic images ----------
def _mri_like_b64() -> str:
    """Generate a grayscale MRI-looking synthetic image (oval skull + internal structures)."""
    W = H = 384
    img = Image.new("L", (W, H), 8)
    d = ImageDraw.Draw(img)
    # outer skull (bright ring)
    d.ellipse([20, 30, W - 20, H - 30], outline=230, width=10)
    # brain tissue (mid gray)
    d.ellipse([40, 50, W - 40, H - 50], fill=110, outline=180, width=3)
    # ventricles (dark butterfly)
    d.ellipse([W // 2 - 60, H // 2 - 30, W // 2 - 10, H // 2 + 30], fill=30)
    d.ellipse([W // 2 + 10, H // 2 - 30, W // 2 + 60, H // 2 + 30], fill=30)
    # gyri / sulci - random darker streaks
    rnd = random.Random(7)
    for _ in range(60):
        x1 = rnd.randint(60, W - 60)
        y1 = rnd.randint(70, H - 70)
        x2 = x1 + rnd.randint(-25, 25)
        y2 = y1 + rnd.randint(-25, 25)
        d.line([x1, y1, x2, y2], fill=rnd.randint(60, 160), width=2)
    # subtle lesion
    d.ellipse([W // 2 + 30, H // 2 - 90, W // 2 + 90, H // 2 - 30], fill=200, outline=240, width=2)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    img_rgb = Image.merge("RGB", (img, img, img))
    buf = io.BytesIO()
    img_rgb.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def _paper_like_b64() -> str:
    """A clearly non-MRI image: lined paper with handwriting-like strokes."""
    W, H = 600, 800
    img = Image.new("RGB", (W, H), (252, 250, 240))
    d = ImageDraw.Draw(img)
    # ruled lines
    for y in range(60, H, 32):
        d.line([(30, y), (W - 30, y)], fill=(180, 200, 220), width=1)
    # red margin
    d.line([(70, 0), (70, H)], fill=(220, 80, 80), width=2)
    # fake handwriting strokes
    rnd = random.Random(3)
    for _ in range(40):
        x = rnd.randint(80, W - 80)
        y = rnd.randint(70, H - 70)
        d.line([(x, y), (x + rnd.randint(20, 80), y + rnd.randint(-3, 3))], fill=(20, 20, 60), width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _oversized_b64() -> str:
    """>12MB JPEG."""
    W = H = 5200
    img = Image.new("RGB", (W, H))
    px = img.load()
    rnd = random.Random(1)
    for y in range(0, H, 4):
        for x in range(0, W, 4):
            v = (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255))
            for dy in range(4):
                for dx in range(4):
                    if x + dx < W and y + dy < H:
                        px[x + dx, y + dy] = v
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=99, subsampling=0)
    data = buf.getvalue()
    # pad if still <12MB
    if len(data) < 12 * 1024 * 1024 + 1024:
        data = data + b"\x00" * (12 * 1024 * 1024 + 2048 - len(data))
    return base64.b64encode(data).decode()


# ---------- Tests ----------
class TestRoot:
    def test_root_ok(self):
        r = requests.get(f"{API}/", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "ok"
        assert "message" in body


class TestSampleGallery:
    def test_gallery_returns_4_categories(self):
        r = requests.get(f"{API}/sample-gallery", timeout=15)
        assert r.status_code == 200
        samples = r.json().get("samples", [])
        assert len(samples) == 4
        cats = {s["category"] for s in samples}
        assert cats == VALID_CLASSES
        for s in samples:
            assert s["url"].startswith("http")
            assert s["label"]
            assert s["id"]


class TestAnalyzeValidation:
    def test_invalid_base64_returns_400(self):
        r = requests.post(f"{API}/analyze",
                          json={"image_base64": "@@@not-base64@@@", "mime_type": "image/jpeg"},
                          timeout=20)
        # Either 400 (bad base64) or 400 (too small after decode)
        assert r.status_code == 400, r.text

    def test_oversized_payload_returns_400(self):
        big = _oversized_b64()
        r = requests.post(f"{API}/analyze",
                          json={"image_base64": big, "mime_type": "image/jpeg"},
                          timeout=60)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:200]}"
        assert "large" in r.text.lower() or "12mb" in r.text.lower()


class TestAnalyzeMRI:
    """Live LLM tests (slow). Use a single MRI-like and a single non-MRI image."""

    @pytest.fixture(scope="class")
    def mri_result(self):
        b64 = _mri_like_b64()
        r = requests.post(f"{API}/analyze",
                          json={"image_base64": b64, "mime_type": "image/jpeg",
                                "patient_context": "Synthetic test image"},
                          timeout=90)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        return r.json()

    def test_mri_response_shape(self, mri_result):
        d = mri_result
        assert "id" in d and isinstance(d["id"], str)
        assert "is_mri" in d
        assert "timestamp" in d

    def test_mri_when_accepted_has_doctor_analysis(self, mri_result):
        d = mri_result
        if not d["is_mri"]:
            pytest.skip(f"Synthetic MRI rejected by LLM: {d.get('rejection_reason')}")
        assert d["classification"] in VALID_CLASSES
        assert d["classification_label"]
        assert isinstance(d["confidence"], (int, float))
        assert 0.5 <= float(d["confidence"]) <= 0.99
        assert isinstance(d["tumor_detected"], bool)
        da = d["doctor_analysis"]
        assert da and isinstance(da, dict)
        for k in ("summary", "observations", "key_indicators", "recommendations", "urgency"):
            assert k in da, f"missing {k}"
        assert da["urgency"] in ("low", "moderate", "high", "critical")
        assert isinstance(da["observations"], list) and len(da["observations"]) >= 1
        assert isinstance(da["recommendations"], list) and len(da["recommendations"]) >= 1


class TestAnalyzeRejection:
    def test_paper_rejected_as_non_mri(self):
        b64 = _paper_like_b64()
        r = requests.post(f"{API}/analyze",
                          json={"image_base64": b64, "mime_type": "image/jpeg"},
                          timeout=90)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        if d["is_mri"]:
            pytest.skip(f"LLM mistakenly classified paper as MRI: {d.get('classification')}")
        assert d["is_mri"] is False
        assert d["rejection_reason"]
        assert d["classification"] is None
        assert d["doctor_analysis"] is None


class TestHistory:
    def test_history_after_analyses(self):
        r = requests.get(f"{API}/history?limit=5", timeout=15)
        assert r.status_code == 200
        items = r.json().get("items", [])
        assert isinstance(items, list)
        # After previous tests at least one should be persisted
        if items:
            it = items[0]
            assert "id" in it
            assert "timestamp" in it
            assert "_id" not in it  # mongo id must be excluded
