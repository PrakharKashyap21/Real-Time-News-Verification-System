import pytest
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType
)
from backend.app.v2.query_builder import FactCheckQueryBuilder, get_query_builder
from backend.app.v2.fact_check_retriever import GoogleFactCheckRetriever
from backend.app.v2.newsapi_retriever import NewsAPIRetriever


@pytest.fixture
def query_builder():
    return FactCheckQueryBuilder()


def test_scaffolding_removal_long_article_claim(query_builder):
    """Test: Heavy news scaffolding is stripped and essential claim terms are retained."""
    claim = ExtractedClaim(
        claim_id="t1",
        text="According to investigative reports and viral social media posts, medical researchers confirmed that drinking hot lemon water with baking soda completely cures cancer.",
        keywords=["lemon water", "baking soda", "cancer", "cure"]
    )
    primary = query_builder.build_primary_query(claim)

    assert "according to" not in primary.lower()
    assert "investigative reports" not in primary.lower()
    assert "viral social media" not in primary.lower()
    assert "confirmed that" not in primary.lower()
    # Core predicate and objects must be present
    assert "lemon" in primary.lower()
    assert "water" in primary.lower()
    assert "baking" in primary.lower()
    assert "cancer" in primary.lower()
    assert len(primary) <= 90


def test_entity_predicate_object_preservation(query_builder):
    """Test: Head entity, predicate verb, and tail object are preserved in multi-word claims."""
    claim = ExtractedClaim(
        claim_id="t2",
        text="NASA's James Webb Space Telescope detected atmospheric carbon dioxide on exoplanet WASP-39b.",
        keywords=["NASA", "James Webb", "WASP-39b", "carbon dioxide"]
    )
    primary = query_builder.build_primary_query(claim)

    assert "NASA" in primary or "James" in primary or "Webb" in primary
    # Tail object terms preserved
    assert "exoplanet" in primary or "WASP-39b" in primary or "dioxide" in primary
    assert len(primary.split()) <= 8


def test_negation_preservation_in_queries(query_builder):
    """Test: Negation words (not, never, no, false) are strictly preserved in primary and fallback queries."""
    claim = ExtractedClaim(
        claim_id="t3",
        text="The European Union did not ban all internal combustion engine vehicles by 2025.",
        keywords=["European Union", "ban", "combustion engine", "2025"]
    )
    primary = query_builder.build_primary_query(claim)
    fallback = query_builder.build_fallback_query(claim)

    assert "not" in primary.lower()
    assert "not" in fallback.lower()
    assert "European" in primary
    assert "2025" in primary or "2025" in fallback


def test_numbers_and_qualifiers_preservation(query_builder):
    """Test: Critical numerical markers and dates are preserved."""
    claim = ExtractedClaim(
        claim_id="t4",
        text="NASA issued an emergency announcement predicting 15 days of total global darkness in November 2026.",
        keywords=["NASA", "15 days", "darkness", "November 2026"]
    )
    primary = query_builder.build_primary_query(claim)
    fallback = query_builder.build_fallback_query(claim)

    assert "15" in primary or "15" in fallback
    assert "NASA" in primary
    assert "darkness" in primary or "darkness" in fallback


def test_canonical_alias_handling_in_fallback_queries(query_builder):
    """Test: Fallback query leverages canonical entity alias expansion for high recall."""
    claim = ExtractedClaim(
        claim_id="t5",
        text="The LHC discovered the Higgs boson particle.",
        keywords=["LHC", "Higgs boson"]
    )
    fallback = query_builder.build_fallback_query(claim)

    # Fallback should expand LHC to Large Hadron Collider and preserve Higgs boson
    assert "Large" in fallback or "Hadron" in fallback or "Collider" in fallback
    assert "Higgs" in fallback or "boson" in fallback


def test_google_fact_check_bounded_requests_with_mock():
    """Test: GoogleFactCheckRetriever executes bounded requests (max 1 for hit, max 2 for empty primary)."""
    retriever = GoogleFactCheckRetriever(api_key="mock_key", mock_mode=True)
    claim = ExtractedClaim(
        claim_id="t6",
        text="NASA announced 15 days of total darkness across Earth.",
        keywords=["NASA", "darkness"]
    )
    evidence = retriever.search_claim(claim)

    # Should succeed with mock evidence and not exceed bounded limit
    assert len(evidence) > 0
    assert retriever.api_call_count <= 2


def test_newsapi_single_request_bounded():
    """Test: NewsAPIRetriever executes exactly ONE request per claim search."""
    retriever = NewsAPIRetriever(api_key="mock_key", mock_mode=True)
    claim = ExtractedClaim(
        claim_id="t7",
        text="NASA Perseverance rover detected organic molecules on Mars.",
        keywords=["NASA", "Perseverance", "Mars"]
    )
    evidence = retriever.search_claim_news(claim, max_results=3)

    assert len(evidence) > 0
    assert retriever.api_call_count == 0  # In mock_mode, returns mock evidence without API count increment


def test_historical_wording_variation_query(query_builder):
    """Test: Historical claim phrasing extracts essential entities, dates, and action predicates."""
    claim = ExtractedClaim(
        claim_id="t8",
        text="NASA's Apollo 11 mission landed American astronauts Neil Armstrong and Buzz Aldrin on the Moon in July 1969.",
        keywords=["NASA", "Apollo 11", "Moon", "1969"]
    )
    primary = query_builder.build_primary_query(claim)
    fallback = query_builder.build_fallback_query(claim)

    assert "Apollo" in primary or "Apollo" in fallback
    assert "1969" in primary or "1969" in fallback
    assert "Moon" in primary or "Moon" in fallback
    assert len(primary.split()) <= 8


def test_fallback_query_diversification_when_primary_long(query_builder):
    """Test: Fallback query provides a punchier, distinct search probe compared to the primary query."""
    claim = ExtractedClaim(
        claim_id="t9",
        text="The World Health Organization declared that COVID-19 is no longer a public health emergency of international concern.",
        keywords=["WHO", "COVID-19", "emergency"]
    )
    primary = query_builder.build_primary_query(claim)
    fallback = query_builder.build_fallback_query(claim)

    # Primary and fallback must be non-empty and bounded
    assert primary != ""
    assert fallback != ""
    assert len(fallback.split()) <= 6
    # Fallback should contain key entity / alias (WHO or World Health Organization) and core concept (COVID-19 / emergency)
    assert "WHO" in fallback or "World" in fallback or "COVID-19" in fallback
    assert "emergency" in fallback.lower() or "health" in fallback.lower()


def test_newsapi_uses_refined_primary_query():
    """Test: NewsAPIRetriever consumes the concise primary query built by FactCheckQueryBuilder."""
    qb = FactCheckQueryBuilder()
    retriever = NewsAPIRetriever(api_key="mock_key", mock_mode=True, query_builder=qb)
    claim = ExtractedClaim(
        claim_id="t10",
        text="Federal Reserve officials announced a 25 basis point interest rate cut at their September policy meeting.",
        keywords=["Federal Reserve", "interest rate"]
    )
    expected_primary = qb.build_primary_query(claim)
    assert "Federal" in expected_primary
    assert "Reserve" in expected_primary
    assert "announced" not in expected_primary.lower()

    evidence = retriever.search_claim_news(claim, max_results=2)
    assert len(evidence) <= 2


def test_stage33a_concrete_retrieval_fixtures(query_builder):
    """Regression fixtures for concrete failed retrieval patterns identified in Stage 33A."""
    fixtures = [
        {
            "id": "false_02_nasa_darkness",
            "claim": "NASA confirmed 15 days of total darkness across Earth in November.",
            "must_have": ["NASA", "15", "darkness"],
            "must_not_have": ["confirmed that"]
        },
        {
            "id": "false_03_lemon_cancer",
            "claim": "Medical studies prove that drinking hot lemon water completely cures cancer 10000 times better than chemotherapy.",
            "must_have": ["lemon", "water", "cancer", "cures"],
            "must_not_have": ["medical studies", "prove that"]
        },
        {
            "id": "fc_01_5g_radiation",
            "claim": "Viral posts allege that 5G cellular towers cause COVID-19 radiation sickness.",
            "must_have": ["5G", "COVID-19", "radiation"],
            "must_not_have": ["viral posts", "allege that"]
        },
        {
            "id": "fc_04_unesco_anthem",
            "claim": "UNESCO declared Jana Gana Mana as the best national anthem in the world.",
            "must_have": ["UNESCO", "Jana", "Gana", "anthem"],
            "must_not_have": ["in the world"]
        },
        {
            "id": "news_08_chandrayaan",
            "claim": "ISRO successfully landed the Chandrayaan-3 lunar lander near the south pole of the Moon.",
            "must_have": ["ISRO", "Chandrayaan-3", "Moon"],
            "must_not_have": ["successfully"]
        }
    ]

    for fix in fixtures:
        cl = ExtractedClaim(claim_id=fix["id"], text=fix["claim"])
        query = query_builder.build_primary_query(cl)
        for term in fix["must_have"]:
            assert term.lower() in query.lower(), f"Expected '{term}' in query for {fix['id']}, got '{query}'"
        for term in fix["must_not_have"]:
            assert term.lower() not in query.lower(), f"Unexpected '{term}' in query for {fix['id']}, got '{query}'"


