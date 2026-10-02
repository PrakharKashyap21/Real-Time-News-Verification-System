"""
Tests for Stage 40 Quota-Safe Evaluation Runner & Request Budgeting.

Verifies:
1. NEWSAPI_BENCHMARK_MAX_REQUESTS is defined and equals 99.
2. NewsAPIBudgetTracker separates preflight and benchmark requests.
3. Request budget enforcement allows up to 99 benchmark requests and blocks further calls.
4. No NewsAPI network calls occur after budget exhaustion.
5. Remaining claims continue executing with Google Fact Check + Reference retrievers.
6. Quota exhaustion is recorded explicitly in service status and tracker metrics.
7. No duplicate NewsAPI requests are issued per claim.
8. Deterministic claim and provider ordering is preserved.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import List

from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType,
    VerificationRequest,
    ClaimVerdict
)
from backend.app.v2.newsapi_retriever import NewsAPIRateLimitError, NewsAPIError
from backend.app.v2.verification_service import VerificationService
from backend.evaluation.run_real_world_evaluation import (
    NEWSAPI_BENCHMARK_MAX_REQUESTS,
    NewsAPIBudgetTracker,
    QuotaSafeNewsAPIRetriever,
    run_newsapi_preflight,
    run_real_world_evaluation
)


def test_budget_constant_and_tracker_accounting():
    """Verifies default budget constant is 99 and preflight is counted separately."""
    assert NEWSAPI_BENCHMARK_MAX_REQUESTS == 99

    tracker = NewsAPIBudgetTracker(max_benchmark_requests=99)
    assert tracker.max_benchmark_requests == 99
    assert tracker.preflight_requests == 0
    assert tracker.benchmark_requests_made == 0
    assert tracker.total_requests == 0
    assert tracker.claims_skipped_budget == 0
    assert not tracker.budget_exhausted

    # Record 1 preflight
    tracker.record_preflight(1)
    assert tracker.preflight_requests == 1
    assert tracker.benchmark_requests_made == 0
    assert tracker.total_requests == 1
    assert not tracker.budget_exhausted

    summary = tracker.get_summary()
    assert summary["preflight_requests"] == 1
    assert summary["benchmark_requests_made"] == 0
    assert summary["total_requests"] == 1
    assert summary["max_benchmark_requests"] == 99


def test_request_budget_enforcement_at_99_limit():
    """Verifies that exactly 99 requests are permitted and the 100th is blocked."""
    tracker = NewsAPIBudgetTracker(max_benchmark_requests=99)
    tracker.record_preflight(1)

    # Make 99 benchmark requests
    for i in range(99):
        allowed = tracker.record_request_attempt()
        assert allowed is True, f"Request {i+1} should be allowed within budget"

    assert tracker.benchmark_requests_made == 99
    assert tracker.claims_with_newsapi == 99
    assert tracker.total_requests == 100  # 1 preflight + 99 benchmark
    assert tracker.budget_exhausted is True
    assert tracker.claims_skipped_budget == 0

    # 100th attempt must be rejected
    rejected_attempt = tracker.record_request_attempt()
    assert rejected_attempt is False
    assert tracker.benchmark_requests_made == 99  # Does not increment
    assert tracker.claims_skipped_budget == 1
    assert tracker.total_requests == 100


def test_no_newsapi_calls_after_budget_exhaustion():
    """Verifies that QuotaSafeNewsAPIRetriever does NOT invoke underlying retriever once budget is exhausted."""
    mock_underlying = MagicMock()
    mock_underlying.search_claim_news.return_value = [
        EvidenceItem(
            id="ev_news_1",
            claim_id="claim_1",
            source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
            publisher="Example News",
            domain="example.com",
            url="https://example.com/article",
            title="Quantum breakthrough announced",
            snippet="Scientists announce quantum computing milestone.",
            stance=StanceType.SUPPORTS
        )
    ]
    mock_underlying.query_builder.build_primary_query.return_value = "quantum supremacy"

    tracker = NewsAPIBudgetTracker(max_benchmark_requests=2)
    safe_retriever = QuotaSafeNewsAPIRetriever(mock_underlying, tracker=tracker)

    claim = ExtractedClaim(claim_id="claim_1", text="Quantum computer achieves breakthrough")

    # 1st call -> allowed
    ev1 = safe_retriever.search_claim_news(claim)
    assert len(ev1) == 1
    assert mock_underlying.search_claim_news.call_count == 1

    # 2nd call -> allowed
    ev2 = safe_retriever.search_claim_news(claim)
    assert len(ev2) == 1
    assert mock_underlying.search_claim_news.call_count == 2
    assert tracker.budget_exhausted is True

    # 3rd call -> budget exhausted, raises NewsAPIRateLimitError without calling mock_underlying
    with pytest.raises(NewsAPIRateLimitError) as exc_info:
        safe_retriever.search_claim_news(claim)

    assert "budget exhausted" in str(exc_info.value)
    # mock_underlying must NOT have been called a 3rd time
    assert mock_underlying.search_claim_news.call_count == 2
    assert tracker.claims_skipped_budget == 1


def test_remaining_claims_still_execute_with_other_providers():
    """Verifies that when NewsAPI budget is exhausted, VerificationService continues with Fact Check & Reference."""
    # Setup mock fact check & reference retrievers
    mock_fc = MagicMock()
    mock_fc.search_claim.return_value = [
        EvidenceItem(
            id="fc_1",
            claim_id="claim_1",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="FactCheck.org",
            domain="factcheck.org",
            url="https://factcheck.org/entry",
            title="Fact check debunk",
            snippet="Fact check verifies claim is completely false.",
            stance=StanceType.CONTRADICTS
        )
    ]

    mock_ref = MagicMock()
    mock_ref.search_claim_reference.return_value = [
        EvidenceItem(
            id="ref_1",
            claim_id="claim_1",
            source_type=EvidenceSourceType.GENERAL_REFERENCE,
            publisher="Wikipedia",
            domain="en.wikipedia.org",
            url="https://en.wikipedia.org/wiki/Topic",
            title="Topic",
            snippet="Wikipedia reference background topic.",
            stance=StanceType.NEUTRAL
        )
    ]

    mock_news = MagicMock()
    mock_news.query_builder.build_primary_query.return_value = "test query"
    mock_news.search_claim_news.return_value = []

    # Budget of 0 benchmark requests (immediately exhausted)
    tracker = NewsAPIBudgetTracker(max_benchmark_requests=0)
    safe_news = QuotaSafeNewsAPIRetriever(mock_news, tracker=tracker)

    service = VerificationService(
        fc_retriever=mock_fc,
        news_retriever=safe_news,
        reference_retriever=mock_ref,
        mock_mode=True
    )

    req = VerificationRequest(title="Breaking news claim", text="The Moon is made of green cheese.")
    response = service.verify_news(req)

    # Verification must succeed and return a valid assessment
    assert response is not None
    assert response.overall_assessment in ["CONTRADICTED", "SUPPORTED", "UNVERIFIED"]
    assert response.service_status.get("live_news_api") == "rate_limited"
    assert response.service_status.get("fact_check_api") == "ok"
    assert response.service_status.get("reference_api") == "ok"

    # NewsAPI underlying retriever was never called
    assert mock_news.search_claim_news.call_count == 0
    # Other providers were called
    assert mock_fc.search_claim.call_count > 0
    assert mock_ref.search_claim_reference.call_count > 0


def test_quota_exhaustion_recorded_explicitly_in_accounting():
    """Verifies that quota exhaustion is transparently reported in summary metrics."""
    tracker = NewsAPIBudgetTracker(max_benchmark_requests=3)
    tracker.record_preflight(1)

    for _ in range(3):
        tracker.record_request_attempt()

    # 4th and 5th claims arrive after quota exhaustion
    tracker.record_request_attempt()
    tracker.record_request_attempt()

    summary = tracker.get_summary()
    assert summary["max_benchmark_requests"] == 3
    assert summary["preflight_requests"] == 1
    assert summary["benchmark_requests_made"] == 3
    assert summary["total_requests"] == 4
    assert summary["claims_evaluated_with_newsapi"] == 3
    assert summary["claims_skipped_budget_exhaustion"] == 2
    assert summary["budget_exhausted"] is True


def test_no_duplicate_newsapi_requests_per_claim():
    """Verifies each claim triggers at most 1 NewsAPI request within budget and 0 after exhaustion."""
    mock_underlying = MagicMock()
    mock_underlying.query_builder.build_primary_query.return_value = "query"
    mock_underlying.search_claim_news.return_value = []

    tracker = NewsAPIBudgetTracker(max_benchmark_requests=1)
    safe_retriever = QuotaSafeNewsAPIRetriever(mock_underlying, tracker=tracker)

    claim1 = ExtractedClaim(claim_id="claim_1", text="Claim one")
    claim2 = ExtractedClaim(claim_id="claim_2", text="Claim two")

    # Claim 1 executes exactly once
    safe_retriever.search_claim_news(claim1)
    assert mock_underlying.search_claim_news.call_count == 1
    assert tracker.benchmark_requests_made == 1

    # Claim 2 cannot execute
    with pytest.raises(NewsAPIRateLimitError):
        safe_retriever.search_claim_news(claim2)

    assert mock_underlying.search_claim_news.call_count == 1
    assert tracker.benchmark_requests_made == 1
    assert tracker.claims_skipped_budget == 1


def test_deterministic_result_ordering():
    """Verifies deterministic behavior: claims in the same order always hit budget at the identical step."""
    def simulate_sequence(budget: int, claim_count: int):
        tracker = NewsAPIBudgetTracker(max_benchmark_requests=budget)
        mock_underlying = MagicMock()
        mock_underlying.query_builder.build_primary_query.return_value = "query"
        mock_underlying.search_claim_news.return_value = []
        safe_retriever = QuotaSafeNewsAPIRetriever(mock_underlying, tracker=tracker)

        results = []
        for i in range(claim_count):
            c = ExtractedClaim(claim_id=f"claim_{i+1}", text=f"Claim {i+1}")
            try:
                safe_retriever.search_claim_news(c)
                results.append("ok")
            except NewsAPIRateLimitError:
                results.append("budget_exhausted")
        return results

    seq1 = simulate_sequence(budget=3, claim_count=6)
    seq2 = simulate_sequence(budget=3, claim_count=6)

    assert seq1 == ["ok", "ok", "ok", "budget_exhausted", "budget_exhausted", "budget_exhausted"]
    assert seq1 == seq2


def test_run_real_world_evaluation_mock_accounting():
    """Verifies that run_real_world_evaluation includes complete quota accounting in metrics in mock mode."""
    res = run_real_world_evaluation(
        mock_mode=True,
        start_idx=0,
        limit=2,
        max_newsapi_requests=1,
        run_preflight_check=False
    )

    assert "newsapi_accounting" in res
    accounting = res["newsapi_accounting"]
    assert accounting["max_benchmark_requests"] == 1
    assert "benchmark_requests_made" in accounting
    assert "claims_evaluated_with_newsapi" in accounting
    assert "claims_skipped_budget_exhaustion" in accounting

    metrics = res["metrics"]
    assert "newsapi_benchmark_max_requests" in metrics
    assert "newsapi_benchmark_requests_made" in metrics
    assert "newsapi_claims_evaluated" in metrics
    assert "newsapi_claims_skipped_budget" in metrics
