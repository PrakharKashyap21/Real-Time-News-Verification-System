import pytest
from unittest.mock import patch, MagicMock
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType,
    VerificationRequest,
    ClaimVerdict,
    OverallAssessment
)
from backend.app.v2.reference_retriever import (
    WikipediaReferenceRetriever,
    ReferenceRetrieverError,
    ReferenceRetrieverAPIError,
    ReferenceRetrieverRateLimitError,
    ReferenceRetrieverTimeoutError,
    ReferenceRetrieverMalformedResponseError,
    strip_html_tags,
    get_reference_retriever
)
from backend.app.v2.verification_service import VerificationService
from backend.app.v2.evidence_matcher import get_evidence_matcher
from backend.app.v2.stance_analyzer import get_stance_analyzer
from backend.app.v2.evidence_aggregator import get_evidence_aggregator
from backend.app.v2.verdict_engine import get_verdict_engine


class TestWikipediaReferenceRetriever:
    """Offline unit tests for WikipediaReferenceRetriever using mocked responses."""

    def test_no_api_key_required(self):
        """Retriever initializes and operates without any API key."""
        retriever = WikipediaReferenceRetriever()
        assert retriever is not None
        assert retriever.mock_mode is False
        assert retriever.max_candidates == 3

    def test_strip_html_tags(self):
        """Removes HTML tags from search snippet markup."""
        raw = 'atoms in the <span class="searchmatch">oxygen</span> <span class="searchmatch">molecule</span> (O2)'
        clean = strip_html_tags(raw)
        assert clean == "atoms in the oxygen molecule (O2)"

    @patch.object(WikipediaReferenceRetriever, "_make_http_get")
    def test_successful_search_and_extract_mapping(self, mock_get):
        """Tests successful search response and summary extract mapping to EvidenceItem."""
        # 1st call: search API, 2nd call: summary API for Molecule
        search_payload = {
            "query": {
                "search": [
                    {
                        "title": "Molecule",
                        "pageid": 19344,
                        "snippet": 'atoms in the <span class="searchmatch">oxygen</span> molecule',
                        "timestamp": "2024-01-15T12:00:00Z"
                    }
                ]
            }
        }
        summary_payload = {
            "title": "Molecule",
            "extract": "A molecule is a group of two or more atoms held together by chemical bonds.",
            "content_urls": {
                "desktop": {
                    "page": "https://en.wikipedia.org/wiki/Molecule"
                }
            },
            "timestamp": "2024-01-15T12:00:00Z"
        }

        mock_get.side_effect = [search_payload, summary_payload]

        retriever = WikipediaReferenceRetriever(max_candidates=1)
        claim = ExtractedClaim(claim_id="c_01", text="Water molecules contain hydrogen and oxygen")
        items = retriever.search_claim_reference(claim)

        assert len(items) == 1
        item = items[0]
        assert item.id == "ref_c_01_1"
        assert item.claim_id == "c_01"
        assert item.source_type == EvidenceSourceType.GENERAL_REFERENCE
        assert item.publisher == "Wikipedia"
        assert item.domain == "en.wikipedia.org"
        assert item.url == "https://en.wikipedia.org/wiki/Molecule"
        assert item.title == "Molecule"
        assert item.snippet == "A molecule is a group of two or more atoms held together by chemical bonds."
        assert item.publish_date == "2024-01-15T12:00:00Z"
        assert item.stance == StanceType.NEUTRAL
        assert item.raw_rating is None
        assert item.credibility_score is None

    @patch.object(WikipediaReferenceRetriever, "_make_http_get")
    def test_empty_search_results(self, mock_get):
        """Returns empty list when search yields zero results."""
        mock_get.return_value = {"query": {"search": []}}
        retriever = WikipediaReferenceRetriever()
        claim = ExtractedClaim(claim_id="c_empty", text="Nonexistent claim query zyxwvutsrqp")
        items = retriever.search_claim_reference(claim)
        assert items == []

    @patch.object(WikipediaReferenceRetriever, "_make_http_get")
    def test_summary_failure_falls_back_to_search_snippet(self, mock_get):
        """If REST summary endpoint fails (e.g. 404), uses cleaned search snippet."""
        search_payload = {
            "query": {
                "search": [
                    {
                        "title": "Rare Subject",
                        "snippet": 'A <span class="searchmatch">rare</span> snippet description.',
                        "timestamp": "2023-05-01T00:00:00Z"
                    }
                ]
            }
        }
        # First call succeeds (search), second call raises 404
        mock_get.side_effect = [
            search_payload,
            ReferenceRetrieverAPIError(404, "Not Found")
        ]

        retriever = WikipediaReferenceRetriever()
        claim = ExtractedClaim(claim_id="c_fallback", text="Rare Subject Event")
        items = retriever.search_claim_reference(claim)

        assert len(items) == 1
        assert items[0].title == "Rare Subject"
        assert items[0].snippet == "A rare snippet description."
        assert items[0].url == "https://en.wikipedia.org/wiki/Rare_Subject"
        assert items[0].stance == StanceType.NEUTRAL

    @patch.object(WikipediaReferenceRetriever, "_make_http_get")
    def test_malformed_json_response(self, mock_get):
        """Raises ReferenceRetrieverMalformedResponseError when response is invalid."""
        mock_get.side_effect = ReferenceRetrieverMalformedResponseError("Invalid JSON")
        retriever = WikipediaReferenceRetriever()
        claim = ExtractedClaim(claim_id="c_bad", text="Some test claim")

        with pytest.raises(ReferenceRetrieverMalformedResponseError):
            retriever.search_claim_reference(claim)

    @patch.object(WikipediaReferenceRetriever, "_make_http_get")
    def test_timeout_error(self, mock_get):
        """Raises ReferenceRetrieverTimeoutError upon timeout."""
        mock_get.side_effect = ReferenceRetrieverTimeoutError("Request timed out")
        retriever = WikipediaReferenceRetriever()
        claim = ExtractedClaim(claim_id="c_to", text="Some test claim")

        with pytest.raises(ReferenceRetrieverTimeoutError):
            retriever.search_claim_reference(claim)

    @patch.object(WikipediaReferenceRetriever, "_make_http_get")
    def test_rate_limit_error(self, mock_get):
        """Raises ReferenceRetrieverRateLimitError upon HTTP 429."""
        mock_get.side_effect = ReferenceRetrieverRateLimitError("Rate limit exceeded")
        retriever = WikipediaReferenceRetriever()
        claim = ExtractedClaim(claim_id="c_rl", text="Some test claim")

        with pytest.raises(ReferenceRetrieverRateLimitError):
            retriever.search_claim_reference(claim)

    def test_empty_claim_input(self):
        """Empty claim or empty text returns empty list without calling API."""
        retriever = WikipediaReferenceRetriever()
        assert retriever.search_claim_reference(None) == []
        assert retriever.search_claim_reference(ExtractedClaim(claim_id="1", text="")) == []

    @patch.object(WikipediaReferenceRetriever, "_make_http_get")
    def test_bounded_request_count(self, mock_get):
        """Ensures request count is strictly bounded by max_candidates."""
        search_payload = {
            "query": {
                "search": [
                    {"title": "Page 1", "snippet": "Snippet 1"},
                    {"title": "Page 2", "snippet": "Snippet 2"},
                    {"title": "Page 3", "snippet": "Snippet 3"},
                    {"title": "Page 4", "snippet": "Snippet 4"},
                    {"title": "Page 5", "snippet": "Snippet 5"}
                ]
            }
        }
        summary_payload = {"title": "Page", "extract": "Extract"}
        mock_get.side_effect = [search_payload, summary_payload, summary_payload]

        retriever = WikipediaReferenceRetriever(max_candidates=2)
        claim = ExtractedClaim(claim_id="c_bound", text="Bounded query test")
        items = retriever.search_claim_reference(claim)

        assert len(items) == 2
        # Total calls: 1 search + 2 summaries = 3 calls
        assert mock_get.call_count == 3


class TestVerificationServiceReferenceIntegration:
    """Integration and isolation tests for VerificationService with general reference provider."""

    def test_provider_isolation_on_reference_failure(self):
        """When MediaWiki fails or times out, other providers continue and service does not crash."""
        mock_fc = MagicMock()
        mock_fc.search_claim.return_value = []

        mock_news = MagicMock()
        mock_news.search_claim_news.return_value = []

        mock_ref = MagicMock()
        mock_ref.search_claim_reference.side_effect = ReferenceRetrieverTimeoutError("Timeout")

        service = VerificationService(
            fc_retriever=mock_fc,
            news_retriever=mock_news,
            reference_retriever=mock_ref,
            mock_mode=True
        )

        req = VerificationRequest(title="Test Article", text="Claim assertion that reference fails on.")
        res = service.verify_news(req)

        assert res is not None
        assert res.service_status["reference_api"] == "timeout"
        assert res.service_status["fact_check_api"] == "ok"
        assert res.service_status["live_news_api"] == "ok"
        assert res.overall_assessment == OverallAssessment.UNVERIFIED

    def test_reference_evidence_remains_neutral_and_unverified_verdict(self):
        """General reference evidence attached to claim must remain NEUTRAL and produce UNVERIFIED verdict."""
        mock_fc = MagicMock()
        mock_fc.search_claim.return_value = []

        mock_news = MagicMock()
        mock_news.search_claim_news.return_value = []

        mock_ref = MagicMock()
        mock_ref.search_claim_reference.side_effect = lambda claim: [
            EvidenceItem(
                id=f"ref_{claim.claim_id}_1",
                claim_id=claim.claim_id,
                source_type=EvidenceSourceType.GENERAL_REFERENCE,
                publisher="Wikipedia",
                domain="en.wikipedia.org",
                url="https://en.wikipedia.org/wiki/Water",
                title="Water Molecule Chemical Composition",
                snippet="Water molecule chemical composition consists of two hydrogen atoms and one oxygen atom.",
                stance=StanceType.NEUTRAL
            )
        ]

        service = VerificationService(
            fc_retriever=mock_fc,
            news_retriever=mock_news,
            reference_retriever=mock_ref,
            mock_mode=True
        )

        req = VerificationRequest(title="", text="Water molecule chemical composition consists of hydrogen and oxygen.")
        res = service.verify_news(req)

        assert len(res.claims) == 1
        claim_detail = res.claims[0]
        # Crucial: Must be UNVERIFIED because reference evidence is NEUTRAL (semantic verifier not yet active)
        assert claim_detail.verdict == ClaimVerdict.UNVERIFIED
        assert claim_detail.neutral_evidence_count >= 1
        assert claim_detail.supporting_evidence_count == 0
        assert claim_detail.contradicting_evidence_count == 0

        # Evidence is preserved in summary
        assert len(claim_detail.evidence) >= 1
        ref_ev = claim_detail.evidence[0]
        assert ref_ev.source_type == EvidenceSourceType.GENERAL_REFERENCE
        assert ref_ev.stance == StanceType.NEUTRAL
        assert ref_ev.domain == "en.wikipedia.org"
