import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def _create_sample_png_bytes(width=200, height=100) -> bytes:
    img = Image.new("RGB", (width, height), color=(20, 30, 40))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_audit_image_unsupported_format():
    response = client.post(
        "/v2/audit-image",
        files={"file": ("malicious.exe", b"binarycontent", "application/octet-stream")}
    )
    assert response.status_code == 422
    assert "Unsupported image format" in response.json()["detail"]

def test_audit_image_empty_file():
    response = client.post(
        "/v2/audit-image",
        files={"file": ("empty.png", b"", "image/png")}
    )
    assert response.status_code == 422

def test_audit_image_success():
    png_bytes = _create_sample_png_bytes(300, 150)
    response = client.post(
        "/v2/audit-image",
        files={"file": ("test_screenshot.png", png_bytes, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_screenshot.png"
    assert "300 x 150" in data["dimensions"]
    assert data["visual_manipulation_risk"] in ["LOW", "MEDIUM", "HIGH"]
    assert "overall_verdict" in data
    assert "extracted_headline" in data
    assert "authenticity_summary" in data
