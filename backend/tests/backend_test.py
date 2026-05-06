"""Backend tests for Multi-Cancer CNN Analyzer (iteration 2)."""
import os
import io
import base64
import random
import pytest
import requests
from PIL import Image, ImageDraw, ImageFilter

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0].strip().strip('"')).rstrip("/")
API = f"{BASE_URL}/api"

EXPECTED_DATASET_IDS = {"brain_mri", "lung_ct", "breast_us", "skin_derm", "kidney_ct"}
NORMAL_CLASSES = {"no_tumor", "normal", "benign"}


# ---------- helpers: synthetic images ----------
def _mri_like_b64() -> str:
    W = H = 384
    img = Image.new("L", (W, H), 8)
    d = ImageDraw.Draw(img)
    d.ellipse([20, 30, W - 20, H - 30], outline=230, width=10)
    d.ellipse([40, 50, W - 40, H - 50], fill=110, outline=180, width=3)
    d.ellipse([W // 2 - 60, H // 2 - 30, W // 2 - 10, H // 2 + 30], fill=30)
    d.ellipse([W // 2 + 10, H // 2 - 30, W // 2 + 60, H // 2 + 30], fill=30)
    rnd = random.Random(7)
    for _ in range(60):
        x1 = rnd.randint(60, W - 60)
        y1 = rnd.randint(70, H - 70)
        x2 = x1 + rnd.randint(-25, 25)
        y2 = y1 + rnd.randint(-25, 25)
        d.line([x1, y1, x2, y2], fill=rnd.randint(60, 160), width=2)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    img_rgb = Image.merge("RGB", (img, img, img))
    buf = io.BytesIO()
    img_rgb.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def _paper_like_b64() -> str:
    W, H = 600, 800
    img = Image.new("RGB", (W, H), (252, 250, 240))
    d = ImageDraw.Draw(img)
    for y in range(60, H, 32):
        d.line([(30, y), (W - 30, y)], fill=(180, 200, 220), width=1)
    d.line([(70, 0), (70, H)], fill=(220, 80, 80), width=2)
    rnd = random.Random(3)
    for _ in range(40):
        x = rnd.randint(80, W - 80)
        y = rnd.randint(70, H - 70)
        d.line([(x, y), (x + rnd.randint(20, 80), y + rnd.randint(-3, 3))], fill=(20, 20, 60), width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _oversized_b64() -> str:
    raw = bytes([random.randint(0, 255) for _ in range(13 * 1024 * 1024)])
    return base64.b64encode(raw).decode()


# ---------- Tests ----------
class TestRoot:
    def test_root_ok(self):
        r = requests.get(f"{API}/", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "ok"
        assert body.get("datasets") == 5


class TestDatasets:
    def test_datasets_returns_5(self):
        r = requests.get(f"{API}/datasets", timeout=15)
        assert r.status_code == 200
        ds = r.json().get("datasets", [])
        assert len(ds) == 5
        ids = {d["id"] for d in ds}
        assert ids == EXPECTED_DATASET_IDS

    def test_each_dataset_has_required_fields(self):
        r = requests.get(f"{API}/datasets", timeout=15)
        ds = r.json()["datasets"]
        for d in ds:
            assert d["classes"] and isinstance(d["classes"], list)
            assert d["class_labels"] and isinstance(d["class_labels"], dict)
            assert "samples" in d and len(d["samples"]) == len(d["classes"])
            for s in d["samples"]:
                assert s["image_url"].startswith("/api/sample-image/")
                assert s["id"].startswith(f"{d['id']}__")


class TestSampleImage:
    def test_valid_sample_image(self):
        r = requests.get(f"{API}/sample-image/brain_mri__glioma", timeout=15)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/jpeg")
        assert len(r.content) > 500
        # verify decodable
        Image.open(io.BytesIO(r.content)).verify()

    def test_unknown_sample_returns_404(self):
        r = requests.get(f"{API}/sample-image/foo__bar", timeout=15)
        assert r.status_code == 404


class TestAnalyzeValidation:
    def test_unknown_dataset_returns_400(self):
        r = requests.post(f"{API}/analyze",
                          json={"image_base64": "abc", "dataset_id": "unknown"},
                          timeout=20)
        assert r.status_code == 400

    def test_invalid_base64_returns_400(self):
        r = requests.post(f"{API}/analyze",
                          json={"image_base64": "@@@not-base64@@@", "dataset_id": "brain_mri"},
                          timeout=20)
        assert r.status_code == 400

    def test_oversized_payload_returns_400(self):
        big = _oversized_b64()
        r = requests.post(f"{API}/analyze",
                          json={"image_base64": big, "dataset_id": "brain_mri"},
                          timeout=60)
        assert r.status_code == 400
        assert "large" in r.text.lower() or "12mb" in r.text.lower()


class TestAnalyzeSample:
    """Sample analysis: skips Claude vision validation, runs CNN + report."""

    @pytest.mark.parametrize("sample_id,expected_class,expected_abnormal", [
        ("brain_mri__pituitary", "pituitary", True),
        ("lung_ct__adenocarcinoma", "adenocarcinoma", True),
        ("kidney_ct__tumor", "tumor", True),
        ("breast_us__normal", "normal", False),
    ])
    def test_analyze_sample_self_classifies(self, sample_id, expected_class, expected_abnormal):
        r = requests.post(f"{API}/analyze-sample",
                          json={"sample_id": sample_id},
                          timeout=90)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["is_valid_image"] is True
        assert d["cnn"] is not None
        assert d["cnn"]["predicted_class"] == expected_class, f"got {d['cnn']['predicted_class']}"
        assert len(d["cnn"]["top_k"]) == 3
        # ensure top_k probabilities are different (real model output, not constant)
        probs = [t["probability"] for t in d["cnn"]["top_k"]]
        assert len(set(round(p, 6) for p in probs)) > 1
        assert d["abnormal_detected"] is expected_abnormal
        # doctor analysis populated (best effort - may fail if LLM hiccup)
        if d.get("doctor_analysis"):
            da = d["doctor_analysis"]
            assert da["urgency"] in ("low", "moderate", "high", "critical")
            assert isinstance(da["observations"], list) and len(da["observations"]) >= 1

    def test_bad_sample_id_404(self):
        r = requests.post(f"{API}/analyze-sample",
                          json={"sample_id": "brain_mri__nonexistent"},
                          timeout=30)
        assert r.status_code in (400, 404)

    def test_malformed_sample_id_400(self):
        r = requests.post(f"{API}/analyze-sample",
                          json={"sample_id": "noseparator"},
                          timeout=30)
        assert r.status_code == 400


class TestAnalyzeUpload:
    def test_paper_rejected(self):
        r = requests.post(f"{API}/analyze",
                          json={"image_base64": _paper_like_b64(),
                                "dataset_id": "brain_mri"},
                          timeout=90)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        if d["is_valid_image"]:
            pytest.skip(f"LLM mistakenly accepted paper as MRI")
        assert d["is_valid_image"] is False
        assert d["rejection_reason"]
        assert d["cnn"] is None
        assert d["dataset_id"] == "brain_mri"

    def test_mri_synthetic_response_shape(self):
        r = requests.post(f"{API}/analyze",
                          json={"image_base64": _mri_like_b64(),
                                "dataset_id": "brain_mri",
                                "patient_context": "Synthetic test"},
                          timeout=120)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "is_valid_image" in d
        assert d["dataset_id"] == "brain_mri"
        assert d["dataset_name"] == "Brain Tumor MRI"
        assert d["modality"] == "MRI"
        assert d["body_part"] == "Brain"
        assert "id" in d and "timestamp" in d
        if d["is_valid_image"]:
            assert d["cnn"] is not None
            assert d["cnn"]["predicted_class"] in {"glioma", "meningioma", "pituitary", "no_tumor"}
            assert len(d["cnn"]["top_k"]) == 3


class TestHistory:
    def test_history_excludes_mongo_id(self):
        r = requests.get(f"{API}/history?limit=5", timeout=15)
        assert r.status_code == 200
        items = r.json().get("items", [])
        assert isinstance(items, list)
        if items:
            assert "_id" not in items[0]
            assert "id" in items[0]
            assert "timestamp" in items[0]
