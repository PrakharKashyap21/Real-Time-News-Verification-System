import time
import threading
from unittest.mock import MagicMock
import pytest

from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType,
    VerificationRequest,
    VerificationResponse,
    OverallAssessment
)
from backend.app.v2.reference_retriever import ReferenceCache, WikipediaReferenceRetriever
from backend.app.v2.semantic_verifier import SemanticVerifier, SemanticRelation
from backend.app.v2.verification_service import VerificationService, get_verification_service


def test_reference_cache_basic_and_ttl():
    """ReferenceCache stores items, enforces TTL expiration, and supports eviction."""
    cache = ReferenceCache(max_size=3, ttl_seconds=0.1)

    cache.set("key1", {"data": 1})
    cache.set("key2", {"data": 2})
    assert cache.get("key1") == {"data": 1}
    assert cache.get("key2") == {"data": 2}
    assert cache.get("nonexistent") is None

    # Test TTL expiration
    time.sleep(0.12)
    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_reference_cache_lru_bounding():
    """ReferenceCache evicts oldest item when exceeding max_size."""
    cache = ReferenceCache(max_size=2, ttl_seconds=10.0)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # 'a' should be evicted

    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.size() == 2


def test_reference_cache_thread_safety():
    """ReferenceCache handles concurrent reads and writes safely."""
    cache = ReferenceCache(max_size=100, ttl_seconds=5.0)

    def worker(worker_id):
        for i in range(50):
            cache.set(f"k_{worker_id}_{i}", i)
            val = cache.get(f"k_{worker_id}_{i}")
            assert val == i or val is None

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert cache.size() <= 100


def test_semantic_verifier_prediction_cache():
    """SemanticVerifier avoids duplicate inference for identical (premise, hypothesis) pairs."""
    verifier = SemanticVerifier(mock_mode=True, cache_max_size=10)
    verifier.clear_cache()
    assert verifier.cache_size() == 0

    pred1 = verifier.verify_pair("Premise text", "Hypothesis statement")
    assert verifier.cache_size() == 1

    # Second call with same pair should hit cache
    pred2 = verifier.verify_pair("Premise text", "Hypothesis statement")
    assert verifier.cache_size() == 1
    assert pred1.semantic_relation == pred2.semantic_relation
    assert pred1.probabilities == pred2.probabilities

    # Different pair creates new cache entry
    verifier.verify_pair("Different premise", "Hypothesis statement")
    assert verifier.cache_size() == 2


def test_verification_service_concurrent_provider_isolation():
    """One provider failing or throwing an exception does not block other providers in concurrent retrieval."""
    service = get_verification_service(mock_mode=True)

    # Setup mock retrievers
    service.fc_retriever.search_claim = MagicMock(side_effect=Exception("FC Timeout"))
    
    mock_news_item = EvidenceItem(
        id="news_1",
        claim_id="claim_1",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="Reuters",
        domain="reuters.com",
        url="https://reuters.com/article1",
        title="Moon Landing Confirmed",
        snippet="NASA confirmed landing on the moon.",
        stance=StanceType.SUPPORTS
    )
    service.news_retriever.search_claim_news = MagicMock(return_value=[mock_news_item])
    service.reference_retriever.search_claim_reference = MagicMock(return_value=[])

    req = VerificationRequest(
        title="Apollo Moon Landing",
        text="Apollo 11 landed astronauts on the Moon in July 1969."
    )

    response = service.verify_news(req)

    assert isinstance(response, VerificationResponse)
    assert response.service_status["fact_check_api"] == "error"
    assert response.service_status["live_news_api"] == "ok"
    assert response.service_status["reference_api"] == "ok"
    assert len(response.claims) > 0


def test_deterministic_evidence_ordering_in_concurrency():
    """Concurrent retrieval preserves strict evidence order: Fact Check -> Live News -> Reference."""
    service = get_verification_service(mock_mode=True)

    fc_item = EvidenceItem(
        id="fc_1",
        claim_id="claim_1",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="FactCheckOrg",
        domain="factcheck.org",
        url="https://factcheck.org/1",
        title="Moon Landing Spaceflight Fact Check",
        snippet="Apollo 11 astronauts landed on the Moon in July 1969.",
        stance=StanceType.SUPPORTS
    )
    news_item = EvidenceItem(
        id="news_1",
        claim_id="claim_1",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="NewsOrg",
        domain="news.org",
        url="https://news.org/1",
        title="Moon Landing Spaceflight Coverage",
        snippet="Apollo 11 astronauts landed on the Moon in July 1969.",
        stance=StanceType.NEUTRAL
    )
    ref_item = EvidenceItem(
        id="ref_1",
        claim_id="claim_1",
        source_type=EvidenceSourceType.GENERAL_REFERENCE,
        publisher="Wikipedia",
        domain="en.wikipedia.org",
        url="https://en.wikipedia.org/wiki/1",
        title="Moon Landing Spaceflight Encyclopedia",
        snippet="Apollo 11 astronauts landed on the Moon in July 1969.",
        stance=StanceType.SUPPORTS
    )

    service.fc_retriever.search_claim = MagicMock(return_value=[fc_item])
    service.news_retriever.search_claim_news = MagicMock(return_value=[news_item])
    service.reference_retriever.search_claim_reference = MagicMock(return_value=[ref_item])

    req = VerificationRequest(
        title="Apollo Moon Landing Spaceflight",
        text="Apollo 11 astronauts landed on the Moon in July 1969."
    )

    response = service.verify_news(req)
    assert len(response.claims) > 0
    claim_ev = response.claims[0].evidence
    assert len(claim_ev) == 3
    assert claim_ev[0].source_type == EvidenceSourceType.FACT_CHECK_API
    assert claim_ev[1].source_type == EvidenceSourceType.LIVE_NEWS_SEARCH
    assert claim_ev[2].source_type == EvidenceSourceType.GENERAL_REFERENCE
