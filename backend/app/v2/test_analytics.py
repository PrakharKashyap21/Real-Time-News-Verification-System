import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_analytics_summary_endpoint():
    response = client.get("/v2/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "engine_metrics" in data
    assert "stance_distribution" in data
    assert "credibility_tiers" in data
    assert "domain_catalog" in data
    assert data["total_tracked_domains"] >= 15
    assert data["engine_metrics"]["benchmark_accuracy_pct"] == 94.2
    assert len(data["credibility_tiers"]) == 5

def test_analytics_domain_filtering():
    # Filter by 'reuters'
    response = client.get("/v2/analytics?domain=reuters")
    assert response.status_code == 200
    data = response.json()
    assert len(data["domain_catalog"]) >= 1
    assert any(d["domain"] == "reuters.com" for d in data["domain_catalog"])

    # Filter by non-existent domain
    response = client.get("/v2/analytics?domain=nonexistentdomain999.xyz")
    assert response.status_code == 200
    data = response.json()
    assert len(data["domain_catalog"]) == 0
