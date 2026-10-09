import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_radar_feed_endpoint():
    response = client.get("/v2/radar")
    assert response.status_code == 200
    data = response.json()
    assert "last_updated" in data
    assert "total_active_stories" in data
    assert "categories" in data
    assert "items" in data
    assert len(data["items"]) >= 4
    first_item = data["items"][0]
    assert "title" in first_item
    assert "summary" in first_item
    assert "prefilled_query" in first_item
    assert "velocity" in first_item

def test_radar_category_filtering():
    response = client.get("/v2/radar?category=Tech%20%26%20AI")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    for item in data["items"]:
        assert "Tech" in item["category"] or "AI" in item["category"]
