import pytest
from backend.app.v2.query_builder import get_query_builder
from backend.app.v2.schemas import ExtractedClaim


@pytest.fixture
def query_builder():
    return get_query_builder()


def test_trent_live_news_query_is_compact_and_proposition_driven(query_builder):
    """Case A: Trent claim generates a high-recall compact query without numbers or verbose dates."""
    claim = ExtractedClaim(
        claim_id="c_trent",
        text="Indian retailer Trent reported a 23% year-on-year rise in standalone revenue in the July-September 2026 quarter.",
        keywords=["Indian", "retailer", "Trent", "reported", "revenue", "rise"]
    )
    query = query_builder.build_news_primary_query(claim)

    assert "Trent" in query
    assert "revenue" in query
    assert len(query) <= 60
    assert "23" not in query
    assert "2026" not in query
    assert "July-September" not in query
    assert "retailer" not in query.lower()


def test_acquisition_query_focuses_on_entities_and_action_without_dollar_amount(query_builder):
    """Case B: Acquisition claim focuses on entities and predicate without requiring transaction dollar amount."""
    claim = ExtractedClaim(
        claim_id="c_acq",
        text="Company X acquired Company Y for $5 billion.",
        keywords=["Company X", "acquired", "Company Y", "billion"]
    )
    query = query_builder.build_news_primary_query(claim)

    assert "Company X" in query or "Company" in query
    assert "acquired" in query or "acquisition" in query
    assert "5" not in query
    assert "billion" not in query.lower()
    assert "$" not in query
    assert len(query) <= 60


def test_space_mission_query_focuses_on_agency_and_mission(query_builder):
    """Case C: NASA space mission claim focuses on agency and mission name."""
    claim = ExtractedClaim(
        claim_id="c_nasa",
        text="NASA successfully launched Artemis to the Moon.",
        keywords=["NASA", "successfully", "launched", "Artemis", "Moon"]
    )
    query = query_builder.build_news_primary_query(claim)

    assert "NASA" in query
    assert "Artemis" in query
    assert len(query) <= 60


def test_conspiracy_query_retains_both_entities(query_builder):
    """Case D: 5G/COVID claim retains both core entities and predicate, does not collapse into single entity."""
    claim = ExtractedClaim(
        claim_id="c_5g",
        text="5G towers spread coronavirus and cause COVID-19 infections.",
        keywords=["5G", "towers", "spread", "coronavirus", "COVID-19"]
    )
    query = query_builder.build_news_primary_query(claim)

    assert "5G" in query
    assert ("coronavirus" in query.lower() or "covid" in query.lower())
    assert len(query) <= 60


def test_verbose_date_range_is_not_mandatory_in_news_query(query_builder):
    """Case E: Claims with verbose calendar ranges strip date strings from news query."""
    claim = ExtractedClaim(
        claim_id="c_date",
        text="Company Alpha reported record profits during the January-March 2025 financial period.",
        keywords=["Company Alpha", "reported", "profits"]
    )
    query = query_builder.build_news_primary_query(claim)

    assert "January-March" not in query
    assert "2025" not in query
    assert "profits" in query or "profit" in query
    assert len(query) <= 60
