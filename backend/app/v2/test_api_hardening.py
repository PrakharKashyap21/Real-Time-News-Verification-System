import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.v2.schemas import (
    VerificationRequest,
    VerificationResponse,
    OverallAssessment
)
from backend.app.v2.verification_service import VerificationService, get_verification_service


@pytest.fixture
def client():
    return TestClient(app)


def test_empty_verification_request_returns_422(client):
    """Empty payload must return a clear 422 validation error."""
    response = client.post("/v2/verify", json={"title": "", "text": ""})
    assert response.status_code == 422
    assert "detail" in response.json()
    detail_str = str(response.json()["detail"]).lower()
    assert "at least one" in detail_str or "validation" in detail_str


def test_short_verification_request_returns_422(client):
    """Very short payload (< 10 chars) must return a clear 422 error."""
    response = client.post("/v2/verify", json={"title": "Hi", "text": "Bye"})
    assert response.status_code == 422
    assert "detail" in response.json()
    detail_str = str(response.json()["detail"]).lower()
    assert "too short" in detail_str or "at least 10" in detail_str


def test_valid_request_returns_well_formed_response(client):
    """Valid verification request returns standard VerificationResponse structure."""
    payload = {
        "title": "NASA Lands Perseverance Rover on Mars",
        "text": "NASA successfully landed its Perseverance rover on the surface of Mars in Jezero Crater.",
        "max_claims": 2
    }
    # Test using mock mode service to prevent external calls in unit test
    mock_service = get_verification_service(mock_mode=True)
    app.dependency_overrides[get_verification_service] = lambda: mock_service
    try:
        response = client.post("/v2/verify", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "overall_assessment" in data
        assert "assessment_summary" in data
        assert "claims" in data
        assert "service_status" in data
        assert "disclaimer" in data
        assert data["overall_assessment"] in ["SUPPORTED", "CONTRADICTED", "UNVERIFIED"]
        assert isinstance(data["claims"], list)
    finally:
        app.dependency_overrides.clear()


def test_internal_server_error_sanitization(client):
    """Internal exceptions must not leak stack traces or internal paths in HTTP response."""
    broken_service = MagicMock(spec=VerificationService)
    broken_service.verify_news.side_effect = RuntimeError("Sensitive internal database path /var/secret/keys failed")

    app.dependency_overrides[get_verification_service] = lambda: broken_service
    try:
        response = client.post("/v2/verify", json={
            "title": "Valid News Headline",
            "text": "Valid news article text content exceeding ten characters."
        })
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        # Ensure sensitive path / error trace is not leaked
        assert "/var/secret" not in data["detail"]
        assert "RuntimeError" not in data["detail"]
        assert "internal error" in data["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_provider_failure_graceful_handling():
    """Service status correctly reflects provider failures without crashing."""
    service = get_verification_service(mock_mode=True)
    # Simulate retriever failures
    service.fc_retriever.search_claim = MagicMock(side_effect=Exception("API Error"))
    service.news_retriever.search_claim_news = MagicMock(side_effect=Exception("Timeout"))
    service.reference_retriever.search_claim_reference = MagicMock(side_effect=Exception("Rate Limit"))

    req = VerificationRequest(
        title="Test Article Headline",
        text="A test statement asserting an unverified claim for error tolerance verification."
    )
    res = service.verify_news(req)
    assert isinstance(res, VerificationResponse)
    assert res.overall_assessment == OverallAssessment.UNVERIFIED
    assert res.service_status["fact_check_api"] == "error"
    assert res.service_status["live_news_api"] == "error"
    assert res.service_status["reference_api"] == "error"
