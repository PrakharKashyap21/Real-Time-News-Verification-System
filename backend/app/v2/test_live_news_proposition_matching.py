import pytest
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType
)
from backend.app.v2.evidence_matcher import EvidenceMatcher, RelevanceClassification
from backend.app.v2.semantic_verifier import SemanticVerifier
from backend.app.v2.verification_service import VerificationService


@pytest.fixture
def matcher():
    return EvidenceMatcher()


@pytest.fixture
def semantic_verifier():
    return SemanticVerifier(mock_mode=False)


# ---------------------------------------------------------------------------
# 1. Trent direct support
# ---------------------------------------------------------------------------
def test_trent_direct_support(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="trent_01",
        text="Indian retailer Trent reported a 23% year-on-year rise in standalone revenue in the July-September 2026 quarter.",
        keywords=["Trent", "revenue", "23%", "retailer"]
    )
    evidence = EvidenceItem(
        id="news_trent_1",
        claim_id="trent_01",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="Reuters",
        domain="reuters.com",
        url="https://www.reuters.com/business/trent-q2-revenue-rises-23-2026",
        title="Trent Q2 results: standalone revenue rises 23% to Rs 4,156 crore",
        snippet="Indian retailer Trent reported a 23% year-on-year rise in standalone revenue in the July-September 2026 quarter, driven by strong store expansion.",
        content="Trent reports 23% rise in standalone revenue during the July-September quarter.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, evidence)
    assert match_res.relevance == RelevanceClassification.RELEVANT
    assert match_res.strong_direct_match is True
    assert match_res.stance == StanceType.SUPPORTS

    processed_items = matcher.process_claim_evidence(claim, [evidence])
    assert len(processed_items) == 1
    assert processed_items[0].stance == StanceType.SUPPORTS

    verified_items = semantic_verifier.process_claim_evidence(claim, processed_items)
    assert verified_items[0].stance == StanceType.SUPPORTS


# ---------------------------------------------------------------------------
# 2. Nobel direct support
# ---------------------------------------------------------------------------
def test_nobel_direct_support(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="nobel_01",
        text="Karl Deisseroth, Peter Hegemann and Georg Nagel won the 2026 Nobel Prize in Physiology or Medicine for discoveries concerning light-gated ion channels and optogenetics.",
        keywords=["Karl Deisseroth", "Peter Hegemann", "Georg Nagel", "Nobel Prize", "optogenetics"]
    )
    evidence = EvidenceItem(
        id="news_nobel_1",
        claim_id="nobel_01",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="Associated Press",
        domain="apnews.com",
        url="https://apnews.com/article/nobel-medicine-optogenetics-2026",
        title="2026 Nobel Prize in Medicine awarded for optogenetics discoveries",
        snippet="Karl Deisseroth, Peter Hegemann and Georg Nagel won the 2026 Nobel Prize in Physiology or Medicine for discoveries concerning light-gated ion channels and optogenetics.",
        content="The Nobel Assembly announced that Karl Deisseroth, Peter Hegemann and Georg Nagel are awarded the 2026 Nobel Prize in Medicine.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, evidence)
    assert match_res.relevance == RelevanceClassification.RELEVANT
    assert match_res.strong_direct_match is True
    assert match_res.stance == StanceType.SUPPORTS

    processed_items = matcher.process_claim_evidence(claim, [evidence])
    verified_items = semantic_verifier.process_claim_evidence(claim, processed_items)
    assert verified_items[0].stance == StanceType.SUPPORTS


# ---------------------------------------------------------------------------
# 3. Nobel wrong reason -> CONTRADICTS or NEUTRAL, NEVER SUPPORTS
# ---------------------------------------------------------------------------
def test_nobel_wrong_reason_never_supports(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="nobel_mismatch",
        text="Karl Deisseroth, Peter Hegemann and Georg Nagel won the 2026 Nobel Prize in Physiology or Medicine for their discoveries in CRISPR gene editing.",
        keywords=["Karl Deisseroth", "Peter Hegemann", "Georg Nagel", "Nobel Prize", "CRISPR", "gene editing"]
    )
    evidence = EvidenceItem(
        id="news_nobel_real",
        claim_id="nobel_mismatch",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="Associated Press",
        domain="apnews.com",
        url="https://apnews.com/article/nobel-medicine-optogenetics-2026",
        title="2026 Nobel Prize in Medicine awarded for optogenetics discoveries",
        snippet="Karl Deisseroth, Peter Hegemann and Georg Nagel won the 2026 Nobel Prize in Physiology or Medicine for discoveries concerning light-gated ion channels and optogenetics.",
        content="The Nobel Prize recognized their discoveries concerning light-gated ion channels and optogenetics.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, evidence)
    assert match_res.strong_direct_match is False
    assert match_res.stance != StanceType.SUPPORTS

    processed_items = matcher.process_claim_evidence(claim, [evidence])
    assert len(processed_items) == 1
    assert processed_items[0].stance != StanceType.SUPPORTS

    verified_items = semantic_verifier.process_claim_evidence(claim, processed_items)
    assert verified_items[0].stance != StanceType.SUPPORTS
    assert verified_items[0].stance in (StanceType.CONTRADICTS, StanceType.NEUTRAL)


# ---------------------------------------------------------------------------
# 4. Exact 5G/COVID -> CONTRADICTS
# ---------------------------------------------------------------------------
def test_exact_5g_covid_contradicts(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="fc_5g_exact",
        text="5G towers spread coronavirus and cause COVID-19 infections.",
        keywords=["5G", "coronavirus", "COVID-19", "spread"]
    )
    fc_evidence = EvidenceItem(
        id="fc_5g_1",
        claim_id="fc_5g_exact",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Full Fact",
        domain="fullfact.org",
        url="https://fullfact.org/online/5g-coronavirus-debunk",
        title="5G does not transmit coronavirus or cause COVID-19",
        snippet="Reviewed Claim: '5G mobile networks spread coronavirus and cause COVID-19 infections' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="5G mobile networks spread coronavirus and cause COVID-19 infections"
    )

    match_res = matcher.match_evidence(claim, fc_evidence)
    assert match_res.relevance == RelevanceClassification.RELEVANT
    assert match_res.stance == StanceType.CONTRADICTS

    processed = matcher.process_claim_evidence(claim, [fc_evidence])
    verified = semantic_verifier.process_claim_evidence(claim, processed)
    assert verified[0].stance == StanceType.CONTRADICTS


# ---------------------------------------------------------------------------
# 5. Paraphrased 5G/COVID -> CONTRADICTS
# ---------------------------------------------------------------------------
def test_paraphrased_5g_covid_contradicts(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="fc_5g_para",
        text="5G mobile networks caused the COVID-19 pandemic by transmitting coronavirus through radio waves.",
        keywords=["5G", "COVID-19", "coronavirus", "radio waves"]
    )
    fc_evidence = EvidenceItem(
        id="fc_5g_2",
        claim_id="fc_5g_para",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Reuters Fact Check",
        domain="reuters.com",
        url="https://www.reuters.com/fact-check/5g-covid-pandemic",
        title="Fact Check: 5G technology does not spread COVID-19 virus",
        snippet="Reviewed Claim: '5G radio waves transmit coronavirus and cause COVID-19 infections' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="5G radio waves transmit coronavirus and cause COVID-19 infections"
    )

    match_res = matcher.match_evidence(claim, fc_evidence)
    assert match_res.relevance == RelevanceClassification.RELEVANT
    assert match_res.stance == StanceType.CONTRADICTS

    processed = matcher.process_claim_evidence(claim, [fc_evidence])
    verified = semantic_verifier.process_claim_evidence(claim, processed)
    assert verified[0].stance == StanceType.CONTRADICTS


# ---------------------------------------------------------------------------
# 6. Generic COVID-only evidence -> rejected
# ---------------------------------------------------------------------------
def test_generic_covid_only_rejected(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="fc_5g_leakage",
        text="5G towers spread coronavirus and cause COVID-19 infections.",
        keywords=["5G", "coronavirus", "COVID-19", "spread"]
    )
    generic_evidence = EvidenceItem(
        id="fc_generic_covid",
        claim_id="fc_5g_leakage",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="HealthFeedback",
        domain="healthfeedback.org",
        url="https://healthfeedback.org/covid-person-to-person",
        title="COVID-19 is an infectious disease spreading among humans",
        snippet="Reviewed Claim: 'COVID-19 does not spread from person to person' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="COVID-19 does not spread from person to person"
    )

    match_res = matcher.match_evidence(claim, generic_evidence)
    assert match_res.relevance == RelevanceClassification.IRRELEVANT
    assert match_res.strong_direct_match is False

    processed = matcher.process_claim_evidence(claim, [generic_evidence])
    assert len(processed) == 0


# ---------------------------------------------------------------------------
# 7. Numeric mismatch -> not SUPPORTS
# ---------------------------------------------------------------------------
def test_numeric_mismatch_not_supports(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="num_claim_1",
        text="Company revenue increased by 23%.",
        keywords=["Company", "revenue", "23%"]
    )
    conflicting_evidence = EvidenceItem(
        id="news_num_1",
        claim_id="num_claim_1",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="Financial Times",
        domain="ft.com",
        url="https://ft.com/company-results",
        title="Company revenue increased by 8%.",
        snippet="Company revenue increased by 8% during the fiscal quarter.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, conflicting_evidence)
    assert match_res.strong_direct_match is False
    assert match_res.stance != StanceType.SUPPORTS

    processed = matcher.process_claim_evidence(claim, [conflicting_evidence])
    verified = semantic_verifier.process_claim_evidence(claim, processed)
    assert verified[0].stance != StanceType.SUPPORTS


# ---------------------------------------------------------------------------
# 8. Future intent vs completed event -> NEUTRAL
# ---------------------------------------------------------------------------
def test_future_intent_vs_completed_event_neutral(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="modal_claim_1",
        text="Company X acquired Company Y for $5 billion.",
        keywords=["Company X", "acquired", "Company Y", "$5 billion"]
    )
    intent_evidence = EvidenceItem(
        id="news_intent_1",
        claim_id="modal_claim_1",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="Bloomberg",
        domain="bloomberg.com",
        url="https://bloomberg.com/deal",
        title="Company X plans to acquire Company Y",
        snippet="Company X plans to acquire Company Y in an upcoming deal.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, intent_evidence)
    assert match_res.strong_direct_match is False
    assert match_res.stance == StanceType.NEUTRAL

    processed = matcher.process_claim_evidence(claim, [intent_evidence])
    verified = semantic_verifier.process_claim_evidence(claim, processed)
    assert verified[0].stance == StanceType.NEUTRAL


# ---------------------------------------------------------------------------
# 9. Subject same but object different -> not SUPPORTS
# ---------------------------------------------------------------------------
def test_subject_same_object_different_not_supports(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="obj_claim_1",
        text="Company Alpha acquired Company Beta.",
        keywords=["Company Alpha", "acquired", "Company Beta"]
    )
    diff_obj_evidence = EvidenceItem(
        id="news_diff_obj_1",
        claim_id="obj_claim_1",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="Reuters",
        domain="reuters.com",
        url="https://reuters.com/deals",
        title="Company Alpha acquired Company Gamma",
        snippet="Company Alpha announced it acquired Company Gamma for cash.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, diff_obj_evidence)
    assert match_res.strong_direct_match is False
    assert match_res.stance != StanceType.SUPPORTS

    processed = matcher.process_claim_evidence(claim, [diff_obj_evidence])
    verified = semantic_verifier.process_claim_evidence(claim, processed)
    assert verified[0].stance != StanceType.SUPPORTS


# ---------------------------------------------------------------------------
# 10. Negation contradiction -> CONTRADICTS
# ---------------------------------------------------------------------------
def test_negation_contradiction(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="neg_claim_1",
        text="NASA successfully landed astronauts on Mars in 2024.",
        keywords=["NASA", "landed", "astronauts", "Mars", "2024"]
    )
    neg_evidence = EvidenceItem(
        id="news_neg_1",
        claim_id="neg_claim_1",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="SpaceNews",
        domain="spacenews.com",
        url="https://spacenews.com/mars",
        title="NASA did not land astronauts on Mars in 2024",
        snippet="NASA has not landed any astronauts on Mars in 2024 or earlier.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, neg_evidence)
    assert match_res.negation_mismatch is True
    assert match_res.stance == StanceType.CONTRADICTS

    processed = matcher.process_claim_evidence(claim, [neg_evidence])
    verified = semantic_verifier.process_claim_evidence(claim, processed)
    assert verified[0].stance == StanceType.CONTRADICTS


# ---------------------------------------------------------------------------
# 11. Equivalent numeric formatting (23% vs 23 percent) -> compatible
# ---------------------------------------------------------------------------
def test_equivalent_numeric_formatting(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="eq_num_claim",
        text="Trent reported a 23% rise in revenue.",
        keywords=["Trent", "23%", "revenue"]
    )
    evidence = EvidenceItem(
        id="news_eq_num_1",
        claim_id="eq_num_claim",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="Reuters",
        domain="reuters.com",
        url="https://reuters.com/trent",
        title="Trent reported a 23 percent increase in revenue",
        snippet="Trent reported a 23 percent increase in revenue for the quarter.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, evidence)
    assert match_res.relevance == RelevanceClassification.RELEVANT
    assert match_res.proposition_diagnostic.get("numeric_match") is True
    assert match_res.strong_direct_match is True
    assert match_res.stance == StanceType.SUPPORTS


# ---------------------------------------------------------------------------
# 12. Equivalent wording/passive-active formulation -> compatible
# ---------------------------------------------------------------------------
def test_equivalent_wording_passive_active(matcher, semantic_verifier):
    claim = ExtractedClaim(
        claim_id="active_claim",
        text="Apple acquired Beats Electronics.",
        keywords=["Apple", "acquired", "Beats Electronics"]
    )
    evidence = EvidenceItem(
        id="news_passive_1",
        claim_id="active_claim",
        source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
        publisher="TechCrunch",
        domain="techcrunch.com",
        url="https://techcrunch.com/apple-beats",
        title="Beats Electronics was acquired by Apple",
        snippet="Beats Electronics was acquired by Apple in a landmark transaction.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, evidence)
    assert match_res.relevance == RelevanceClassification.RELEVANT
    assert match_res.proposition_diagnostic.get("proposition_compatible") is True
    assert match_res.stance == StanceType.SUPPORTS


# ---------------------------------------------------------------------------
# GDELT fallback in VerificationService
# ---------------------------------------------------------------------------
def test_gdelt_fallback_when_newsapi_empty_or_fails():
    """When NewsAPI returns zero results or errors, verification service falls back to GDELT."""
    class MockFailingNewsAPI:
        def search_claim_news(self, claim, max_results=5):
            return []

    class MockWorkingGDELT:
        def search_claim_news(self, claim, max_results=5, timespan="24h"):
            return [
                EvidenceItem(
                    id="gdelt_ev_1",
                    claim_id=claim.claim_id,
                    source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
                    publisher="BBC News",
                    domain="bbc.com",
                    url="https://www.bbc.com/news/live-story-1",
                    title="Breaking News Event Reported",
                    snippet="Current News Report: 'Breaking News Event Reported'",
                    stance=StanceType.NEUTRAL
                )
            ]

    service = VerificationService(
        news_retriever=MockFailingNewsAPI(),
        gdelt_retriever=MockWorkingGDELT(),
        mock_mode=True
    )

    claim = ExtractedClaim(claim_id="test_fallback", text="Some breaking news event occurred.")
    evidence, status = service._fetch_news_evidence(claim)
    assert status == "ok"
    assert len(evidence) == 1
    assert evidence[0].id == "gdelt_ev_1"
