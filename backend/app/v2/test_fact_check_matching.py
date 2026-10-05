import pytest
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType,
    ClaimVerdict,
    VerificationRequest
)
from backend.app.v2.evidence_matcher import EvidenceMatcher, RelevanceClassification
from backend.app.v2.query_builder import FactCheckQueryBuilder
from backend.app.v2.verification_service import VerificationService


@pytest.fixture
def matcher():
    return EvidenceMatcher()


@pytest.fixture
def query_builder():
    return FactCheckQueryBuilder()


def test_exact_same_claim_fact_check_accepted(matcher):
    """Test 1: Exact / same-claim fact-check is accepted as RELEVANT with correct stance."""
    claim = ExtractedClaim(
        claim_id="c1",
        text="UNESCO declared Jana Gana Mana as the best national anthem in the world.",
        keywords=["UNESCO", "Jana Gana Mana", "national anthem"]
    )
    evidence = EvidenceItem(
        id="fc_1",
        claim_id="c1",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Factly",
        domain="factly.in",
        url="https://factly.in/unesco-anthem",
        title="Fact Check: UNESCO national anthem announcement",
        snippet="Reviewed Claim: 'Did UNESCO declare India's Jana Gana Mana the best national anthem in the world?' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="Did UNESCO declare India's Jana Gana Mana as the best national anthem in the world?"
    )

    result = matcher.match_evidence(claim, evidence)
    assert result.relevance == RelevanceClassification.RELEVANT
    assert result.stance == StanceType.CONTRADICTS
    assert "UNESCO" in result.entity_overlap


def test_clearly_unrelated_claim_rejected(matcher):
    """Test 2: Completely unrelated claim is rejected as IRRELEVANT."""
    claim = ExtractedClaim(
        claim_id="c2",
        text="NASA launched the James Webb Space Telescope into orbit.",
        keywords=["NASA", "James Webb", "Telescope"]
    )
    evidence = EvidenceItem(
        id="fc_2",
        claim_id="c2",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Snopes",
        domain="snopes.com",
        url="https://snopes.com/gas-stoves",
        title="Fact Check: European Union gas stove ban",
        snippet="Reviewed Claim: 'Did the European Union ban all gas stoves in restaurants?' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="Did the European Union ban all gas stoves in restaurants?"
    )

    result = matcher.match_evidence(claim, evidence)
    assert result.relevance == RelevanceClassification.IRRELEVANT
    assert result.stance == StanceType.NEUTRAL
    assert "Rejected" in result.matching_explanation


def test_same_entities_different_predicate_rejected(matcher):
    """Test 3: Same entities (NASA, Mars) but completely different predicate/action (discovered bacteria vs photographed face) is rejected."""
    claim = ExtractedClaim(
        claim_id="c3",
        text="NASA discovered living bacteria on Mars.",
        keywords=["NASA", "Mars", "bacteria"]
    )
    evidence = EvidenceItem(
        id="fc_3",
        claim_id="c3",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="USA Today",
        domain="usatoday.com",
        url="https://usatoday.com/mars-face",
        title="Fact Check: NASA photographed pyramid on Mars",
        snippet="Reviewed Claim: 'NASA photographed a strange alien face and pyramid structure on Mars' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="NASA photographed a strange alien face and pyramid structure on Mars"
    )

    result = matcher.match_evidence(claim, evidence)
    assert result.relevance == RelevanceClassification.IRRELEVANT
    assert result.stance == StanceType.NEUTRAL
    assert "Rejected adjacent fact-check" in result.matching_explanation


def test_same_topic_materially_different_claim_rejected(matcher):
    """Test 4: Same broad topic (CERN/LHC) but materially different claim (Higgs boson discovery vs creating black hole) is rejected."""
    claim = ExtractedClaim(
        claim_id="c4",
        text="The Large Hadron Collider discovered the Higgs boson in 2012.",
        keywords=["Large Hadron Collider", "Higgs boson", "2012"]
    )
    evidence = EvidenceItem(
        id="fc_4",
        claim_id="c4",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="AFP Fact Check",
        domain="factcheck.afp.com",
        url="https://factcheck.afp.com/cern-portal",
        title="Fact Check: CERN portal black hole",
        snippet="Reviewed Claim: 'CERN scientists created a black hole that will destroy Earth' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="CERN scientists created a black hole that will destroy Earth"
    )

    result = matcher.match_evidence(claim, evidence)
    assert result.relevance == RelevanceClassification.IRRELEVANT
    assert result.stance == StanceType.NEUTRAL
    assert "Rejected adjacent fact-check" in result.matching_explanation


def test_relevant_contradiction_accepted(matcher):
    """Test 5: Relevant contradiction of a debunked false claim is accepted with CONTRADICTS stance."""
    claim = ExtractedClaim(
        claim_id="c5",
        text="Drinking hot lemon water with baking soda completely cures cancer.",
        keywords=["lemon water", "baking soda", "cures cancer"]
    )
    evidence = EvidenceItem(
        id="fc_5",
        claim_id="c5",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="PolitiFact",
        domain="politifact.com",
        url="https://politifact.com/lemon-cancer",
        title="Fact Check: Lemon water cancer cure",
        snippet="Reviewed Claim: 'Drinking hot lemon water with baking soda cures cancer 10,000 times better than chemo' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="Drinking hot lemon water with baking soda cures cancer 10000 times better than chemotherapy"
    )

    result = matcher.match_evidence(claim, evidence)
    assert result.relevance == RelevanceClassification.RELEVANT
    assert result.stance == StanceType.CONTRADICTS


def test_relevant_support_accepted(matcher):
    """Test 6: Relevant fact check verifying true claim is accepted with SUPPORTS stance."""
    claim = ExtractedClaim(
        claim_id="c6",
        text="WHO ended the COVID-19 global health emergency in May 2023.",
        keywords=["WHO", "COVID-19", "global health emergency", "May 2023"]
    )
    evidence = EvidenceItem(
        id="fc_6",
        claim_id="c6",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Reuters Fact Check",
        domain="reuters.com",
        url="https://reuters.com/fact-check/who-covid-emergency",
        title="Fact Check: WHO COVID-19 emergency status",
        snippet="Reviewed Claim: 'The World Health Organization declared an end to the COVID-19 global health emergency in May 2023' | Rating: True",
        stance=StanceType.SUPPORTS,
        raw_rating="True",
        claim_reviewed="The World Health Organization declared an end to the COVID-19 global health emergency in May 2023"
    )

    result = matcher.match_evidence(claim, evidence)
    assert result.relevance == RelevanceClassification.RELEVANT
    assert result.stance == StanceType.SUPPORTS


def test_missing_claim_reviewed_handled_safely(matcher):
    """Test 7: When claim_reviewed is missing/None, falls back to title safely."""
    # Case 7a: Relevant title match
    claim = ExtractedClaim(
        claim_id="c7a",
        text="NASA's Apollo 11 mission landed humans on the Moon in 1969.",
        keywords=["NASA", "Apollo 11", "Moon", "1969"]
    )
    evidence_valid = EvidenceItem(
        id="fc_7a",
        claim_id="c7a",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="FactCheck.org",
        domain="factcheck.org",
        url="https://factcheck.org/apollo-11",
        title="Fact Check: Did the Apollo 11 mission land humans on the Moon in 1969?",
        snippet="Rating: True",
        stance=StanceType.SUPPORTS,
        raw_rating="True",
        claim_reviewed=None  # Missing
    )

    result_valid = matcher.match_evidence(claim, evidence_valid)
    assert result_valid.relevance == RelevanceClassification.RELEVANT
    assert result_valid.stance == StanceType.SUPPORTS

    # Case 7b: Irrelevant title match
    evidence_irrelevant = EvidenceItem(
        id="fc_7b",
        claim_id="c7a",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Snopes",
        domain="snopes.com",
        url="https://snopes.com/moon-cheese",
        title="Fact Check: Is the Moon made of green cheese?",
        snippet="Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed=None  # Missing
    )

    result_irrel = matcher.match_evidence(claim, evidence_irrelevant)
    assert result_irrel.relevance == RelevanceClassification.IRRELEVANT
    assert result_irrel.stance == StanceType.NEUTRAL


def test_query_builder_focuses_on_extracted_claim(query_builder):
    """Test 8: Query builder generates concise queries preserving entities and key predicates."""
    claim = ExtractedClaim(
        claim_id="c8",
        text="According to viral social media reports, NASA discovered organic carbon molecules in Jezero Crater on Mars.",
        keywords=["NASA", "Perseverance", "Jezero Crater", "Mars"]
    )
    primary_query = query_builder.build_primary_query(claim)

    # Scaffolding must be stripped
    assert "according to" not in primary_query.lower()
    assert "viral social media" not in primary_query.lower()
    # High-value entities and objects must be present
    assert "NASA" in primary_query
    assert "Mars" in primary_query
    assert "discovered" in primary_query
    assert len(primary_query) <= 90


def test_user_claim_vs_unrelated_covid_fact_check_rejected(matcher):
    """Test A: User claim vs unrelated COVID fact-checks missing subject entity (5G) are rejected."""
    claim = ExtractedClaim(
        claim_id="c_5g_unrelated",
        text="5G towers spread coronavirus and cause COVID-19 infections.",
        keywords=["5G", "coronavirus", "COVID-19"]
    )
    unrelated_fc_1 = EvidenceItem(
        id="fc_u1",
        claim_id="c_5g_unrelated",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="HealthFactCheck",
        domain="healthfeedback.org",
        url="https://healthfeedback.org/covid-person-spread",
        title="Fact Check: COVID-19 person-to-person spread",
        snippet="Reviewed Claim: 'COVID-19 does not spread from person to person' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="COVID-19 does not spread from person to person"
    )
    unrelated_fc_2 = EvidenceItem(
        id="fc_u2",
        claim_id="c_5g_unrelated",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Factly",
        domain="factly.in",
        url="https://factly.in/covid-infectious",
        title="Fact Check: Coronavirus infectiousness",
        snippet="Reviewed Claim: 'The coronavirus that causes COVID-19 is infectious' | Rating: True",
        stance=StanceType.SUPPORTS,
        raw_rating="True",
        claim_reviewed="The coronavirus that causes COVID-19 is infectious"
    )

    res1 = matcher.match_evidence(claim, unrelated_fc_1)
    res2 = matcher.match_evidence(claim, unrelated_fc_2)

    assert res1.relevance == RelevanceClassification.IRRELEVANT
    assert res1.stance == StanceType.NEUTRAL
    assert "Rejected" in res1.matching_explanation

    assert res2.relevance == RelevanceClassification.IRRELEVANT
    assert res2.stance == StanceType.NEUTRAL
    assert "Rejected" in res2.matching_explanation


def test_user_claim_vs_directly_aligned_5g_fact_check_accepted(matcher):
    """Test B: Directly aligned fact-check addressing 5G coronavirus proposition is accepted."""
    claim = ExtractedClaim(
        claim_id="c_5g_aligned",
        text="5G towers spread coronavirus and cause COVID-19 infections.",
        keywords=["5G", "coronavirus", "COVID-19"]
    )
    aligned_fc = EvidenceItem(
        id="fc_a1",
        claim_id="c_5g_aligned",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Full Fact",
        domain="fullfact.org",
        url="https://fullfact.org/online/5g-coronavirus-conspiracy",
        title="Fact Check: 5G mobile networks spread coronavirus",
        snippet="Reviewed Claim: '5G mobile towers spread coronavirus and cause COVID-19 infections' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="5G mobile towers spread coronavirus and cause COVID-19 infections"
    )

    res = matcher.match_evidence(claim, aligned_fc)
    assert res.relevance == RelevanceClassification.RELEVANT
    assert res.stance == StanceType.CONTRADICTS
    assert any("5G" in e.upper() for e in res.entity_overlap)


def test_paraphrased_aligned_fact_check_accepted(matcher):
    """Test C: Paraphrased fact-checks with differing phrasing but identical proposition are accepted."""
    claim = ExtractedClaim(
        claim_id="c_5g_para",
        text="5G towers spread coronavirus and cause COVID-19 infections.",
        keywords=["5G", "coronavirus", "COVID-19"]
    )
    para_fc_1 = EvidenceItem(
        id="fc_p1",
        claim_id="c_5g_para",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Reuters Fact Check",
        domain="reuters.com",
        url="https://reuters.com/5g-causes-covid",
        title="Fact Check: 5G technology causes COVID-19",
        snippet="Reviewed Claim: '5G technology causes COVID-19' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="5G technology causes COVID-19"
    )
    para_fc_2 = EvidenceItem(
        id="fc_p2",
        claim_id="c_5g_para",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="PolitiFact",
        domain="politifact.com",
        url="https://politifact.com/5g-networks-coronavirus",
        title="Fact Check: 5G networks spread coronavirus",
        snippet="Reviewed Claim: '5G networks spread coronavirus' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="5G networks spread coronavirus"
    )

    res1 = matcher.match_evidence(claim, para_fc_1)
    res2 = matcher.match_evidence(claim, para_fc_2)

    assert res1.relevance == RelevanceClassification.RELEVANT
    assert res1.stance == StanceType.CONTRADICTS

    assert res2.relevance == RelevanceClassification.RELEVANT
    assert res2.stance == StanceType.CONTRADICTS


def test_generic_topic_overlap_rejected(matcher):
    """Test D: Generic topical overlap (COVID surfaces, vaccines) lacking the 5G entity is rejected."""
    claim = ExtractedClaim(
        claim_id="c_5g_topic",
        text="5G towers spread coronavirus and cause COVID-19 infections.",
        keywords=["5G", "coronavirus", "COVID-19"]
    )
    fc_surface = EvidenceItem(
        id="fc_top1",
        claim_id="c_5g_topic",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="AFP Fact Check",
        domain="factcheck.afp.com",
        url="https://factcheck.afp.com/covid-surfaces",
        title="Fact Check: COVID-19 on surfaces",
        snippet="Reviewed Claim: 'COVID-19 can survive on surfaces for weeks' | Rating: Misleading",
        stance=StanceType.CONTRADICTS,
        raw_rating="Misleading",
        claim_reviewed="COVID-19 can survive on surfaces for weeks"
    )
    fc_vaccines = EvidenceItem(
        id="fc_top2",
        claim_id="c_5g_topic",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="FactCheck.org",
        domain="factcheck.org",
        url="https://factcheck.org/vaccines-transmission",
        title="Fact Check: Vaccines reduce transmission",
        snippet="Reviewed Claim: 'Vaccines reduce COVID-19 transmission' | Rating: True",
        stance=StanceType.SUPPORTS,
        raw_rating="True",
        claim_reviewed="Vaccines reduce COVID-19 transmission"
    )

    res_surface = matcher.match_evidence(claim, fc_surface)
    res_vaccines = matcher.match_evidence(claim, fc_vaccines)

    assert res_surface.relevance == RelevanceClassification.IRRELEVANT
    assert res_vaccines.relevance == RelevanceClassification.IRRELEVANT


def test_fact_check_rating_preserved_when_aligned(matcher):
    """Test E: Fact-check rating semantics (False -> CONTRADICTS, True -> SUPPORTS) are preserved when proposition-aligned."""
    claim_false = ExtractedClaim(
        claim_id="c_rating_false",
        text="5G networks spread coronavirus infections.",
        keywords=["5G", "coronavirus"]
    )
    fc_false = EvidenceItem(
        id="fc_rf",
        claim_id="c_rating_false",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Snopes",
        domain="snopes.com",
        url="https://snopes.com/5g-virus",
        title="Fact Check: 5G networks spread coronavirus",
        snippet="Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="5G networks spread coronavirus"
    )
    res_f = matcher.match_evidence(claim_false, fc_false)
    assert res_f.relevance == RelevanceClassification.RELEVANT
    assert res_f.stance == StanceType.CONTRADICTS

    claim_true = ExtractedClaim(
        claim_id="c_rating_true",
        text="WHO ended the COVID-19 global health emergency in May 2023.",
        keywords=["WHO", "COVID-19", "2023"]
    )
    fc_true = EvidenceItem(
        id="fc_rt",
        claim_id="c_rating_true",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Reuters",
        domain="reuters.com",
        url="https://reuters.com/who-covid-ended",
        title="Fact Check: WHO COVID-19 emergency ended",
        snippet="Rating: True",
        stance=StanceType.SUPPORTS,
        raw_rating="True",
        claim_reviewed="The World Health Organization declared an end to the COVID-19 global health emergency in May 2023"
    )
    res_t = matcher.match_evidence(claim_true, fc_true)
    assert res_t.relevance == RelevanceClassification.RELEVANT
    assert res_t.stance == StanceType.SUPPORTS


def test_apollo_and_temporal_regressions_preserved(matcher):
    """Test F: Existing numbered entity (Apollo 11 vs Apollo 9) and temporal year guardrails remain intact."""
    claim_apollo = ExtractedClaim(
        claim_id="c_apollo_reg",
        text="Apollo 11 landed humans on the Moon in July 1969.",
        keywords=["Apollo 11", "Moon", "1969"]
    )
    adjacent_apollo = EvidenceItem(
        id="fc_ap9",
        claim_id="c_apollo_reg",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="Factly",
        domain="factly.in",
        url="https://factly.in/apollo-9",
        title="Fact Check: Apollo 9 Moon Landing",
        snippet="Reviewed Claim: 'Did the Apollo 9 mission land on the Moon?' | Rating: False",
        stance=StanceType.CONTRADICTS,
        raw_rating="False",
        claim_reviewed="Did the Apollo 9 mission land on the Moon?"
    )
    aligned_apollo = EvidenceItem(
        id="fc_ap11",
        claim_id="c_apollo_reg",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="FactCheck.org",
        domain="factcheck.org",
        url="https://factcheck.org/apollo-11-landing",
        title="Fact Check: Apollo 11 Moon Landing",
        snippet="Reviewed Claim: 'Did the Apollo 11 mission land humans on the Moon in 1969?' | Rating: True",
        stance=StanceType.SUPPORTS,
        raw_rating="True",
        claim_reviewed="Did the Apollo 11 mission land humans on the Moon in 1969?"
    )

    res_adj = matcher.match_evidence(claim_apollo, adjacent_apollo)
    res_aln = matcher.match_evidence(claim_apollo, aligned_apollo)

    assert res_adj.relevance == RelevanceClassification.IRRELEVANT
    assert res_aln.relevance == RelevanceClassification.RELEVANT

    # Temporal year mismatch
    claim_temporal = ExtractedClaim(
        claim_id="c_temp",
        text="A devastating earthquake struck Tokyo in 2024.",
        keywords=["earthquake", "Tokyo", "2024"]
    )
    fc_temporal_mismatch = EvidenceItem(
        id="fc_temp_1923",
        claim_id="c_temp",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="AFP",
        domain="afp.com",
        url="https://afp.com/tokyo-1923",
        title="Fact Check: Great Kanto earthquake",
        snippet="Reviewed Claim: 'The Great Kanto earthquake struck Tokyo in 1923' | Rating: True",
        stance=StanceType.SUPPORTS,
        raw_rating="True",
        claim_reviewed="The Great Kanto earthquake struck Tokyo in 1923"
    )
    res_temp = matcher.match_evidence(claim_temporal, fc_temporal_mismatch)
    assert res_temp.relevance == RelevanceClassification.IRRELEVANT
    assert "Temporal" in res_temp.matching_explanation


def test_deterministic_evidence_ordering_remains_unchanged(matcher):
    """Test G: Deterministic evidence filtering and ordering remains identical across repeated invocations."""
    claim = ExtractedClaim(
        claim_id="c_det",
        text="5G towers spread coronavirus and cause COVID-19 infections.",
        keywords=["5G", "coronavirus", "COVID-19"]
    )
    items = [
        EvidenceItem(
            id="fc_1",
            claim_id="c_det",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="Full Fact",
            domain="fullfact.org",
            url="https://fullfact.org/5g-covid",
            title="Fact Check: 5G spreading COVID-19",
            snippet="Rating: False",
            stance=StanceType.CONTRADICTS,
            raw_rating="False",
            claim_reviewed="5G towers spread coronavirus"
        ),
        EvidenceItem(
            id="fc_2",
            claim_id="c_det",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="Health Feedback",
            domain="healthfeedback.org",
            url="https://healthfeedback.org/covid-spread",
            title="Fact Check: COVID-19 spread",
            snippet="Rating: False",
            stance=StanceType.CONTRADICTS,
            raw_rating="False",
            claim_reviewed="COVID-19 is not infectious"
        ),
        EvidenceItem(
            id="fc_3",
            claim_id="c_det",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="Reuters",
            domain="reuters.com",
            url="https://reuters.com/5g-technology-covid",
            title="Fact Check: 5G technology COVID-19",
            snippet="Rating: False",
            stance=StanceType.CONTRADICTS,
            raw_rating="False",
            claim_reviewed="5G technology causes COVID-19"
        )
    ]

    out1 = matcher.process_claim_evidence(claim, items)
    out2 = matcher.process_claim_evidence(claim, items)

    assert len(out1) == 2  # fc_1 and fc_3 survive; fc_2 rejected
    assert len(out2) == 2
    assert [x.id for x in out1] == ["fc_1", "fc_3"]
    assert [x.id for x in out1] == [x.id for x in out2]
    assert [x.stance for x in out1] == [x.stance for x in out2]

