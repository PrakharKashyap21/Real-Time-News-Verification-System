import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_extract_url_validation_error():
    response = client.post("/v2/extract-url", json={"url": ""})
    assert response.status_code == 422

def test_extract_url_mocked(monkeypatch):
    import trafilatura
    def mock_fetch(url, timeout=6.0):
        return "<html><head><title>SpaceX Launch Success</title></head><body><p>SpaceX successfully launched Starship rocket on its test flight.</p></body></html>"
    
    monkeypatch.setattr(trafilatura, "fetch_url", mock_fetch)
    
    response = client.post("/v2/extract-url", json={"url": "https://example.com/spacex-news"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "SpaceX" in data["title"] or "SpaceX" in data["text"]
    assert data["domain"] == "example.com"
