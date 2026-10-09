import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_audit_document_validation_error():
    response = client.post("/v2/audit-document", json={"content": "too short"})
    assert response.status_code == 422

def test_audit_file_unsupported_format():
    response = client.post(
        "/v2/audit-file",
        files={"file": ("image.png", b"fake image bytes", "image/png")}
    )
    assert response.status_code == 422

def test_audit_document_mocked(monkeypatch):
    from backend.app.v2.rag_verifier import get_rag_verifier
    rag = get_rag_verifier()

    # Mock decompose_claims and _verify_single_claim
    monkeypatch.setattr(
        rag,
        "_decompose_claims",
        lambda title, content: [
            "NASA launched the Artemis I mission to test Orion spacecraft.",
            "5G towers transmit coronavirus pathogens."
        ]
    )

    from backend.app.v2.schemas import ClaimVerdict
    def mock_verify_claim(claim_text, cid):
        if "Artemis" in claim_text:
            return {
                "verdict": ClaimVerdict.SUPPORTED,
                "reasoning": "NASA officially launched Artemis I in 2022.",
                "evidence": [{"publisher": "NASA", "domain": "nasa.gov", "stance": "SUPPORTS"}],
                "supporting_evidence_count": 1,
                "contradicting_evidence_count": 0,
                "neutral_evidence_count": 0,
                "has_conflicting_evidence": False,
                "evidence_strength": "STRONG"
            }
        else:
            return {
                "verdict": ClaimVerdict.CONTRADICTED,
                "reasoning": "Scientific consensus debunks 5G coronavirus claim.",
                "evidence": [{"publisher": "WHO", "domain": "who.int", "stance": "CONTRADICTS"}],
                "supporting_evidence_count": 0,
                "contradicting_evidence_count": 1,
                "neutral_evidence_count": 0,
                "has_conflicting_evidence": False,
                "evidence_strength": "STRONG"
            }

    monkeypatch.setattr(rag, "verify_claim", mock_verify_claim)


    payload = {
        "title": "Science News Audit",
        "content": "This is a full article text covering the Artemis I space exploration and debunking claims about 5G mobile towers causing diseases."
    }

    response = client.post("/v2/audit-document", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["document_title"] == "Science News Audit"
    assert data["total_claims_detected"] == 2
    assert "audited_claims" in data
    assert len(data["audited_claims"]) == 2
    assert data["claims_breakdown"]["supported"] == 1
    assert data["claims_breakdown"]["contradicted"] == 1
    assert data["overall_status"] in ["HIGH_RISK", "MIXED_CREDIBILITY"]
