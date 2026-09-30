import pytest
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType,
    VerificationRequest,
    VerificationResponse
)
from backend.app.v2.reference_retriever import (
    extract_relevant_passage,
    WikipediaReferenceRetriever
)
from backend.app.v2.semantic_verifier import (
    SemanticVerifier,
    SemanticRelation,
    get_semantic_verifier
)
from backend.app.v2.evidence_matcher import (
    EvidenceMatcher,
    RelevanceClassification
)


def test_extract_relevant_passage_selects_specific_claim_sentence():
    """extract_relevant_passage extracts the concise proposition sentence rather than the entire multi-paragraph text."""
    claim = ExtractedClaim(
        claim_id="c1",
        text="Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969."
    )

    broad_extract = (
        "Apollo 11 (July 16–24, 1969) was the American spaceflight that first landed humans on the Moon. "
        "Commander Neil Armstrong and lunar module pilot Buzz Aldrin landed the Apollo Lunar Module Eagle on July 20, 1969. "
        "Aldrin joined him 19 minutes later, and they spent about two hours exploring Tranquility Base. "
        "They collected 47.5 pounds of lunar material to bring back to Earth as pilot Michael Collins flew the Command Module."
    )

    passage = extract_relevant_passage(
        claim=claim,
        page_title="Apollo 11",
        full_extract=broad_extract,
        search_snippet="Apollo 11 moon landing."
    )

    assert "first landed humans on the Moon" in passage
    assert "1969" in passage
    # The passage is focused and does not drag unrelated sentences like Collins and sample weights
    assert "Michael Collins" not in passage or len(passage) < len(broad_extract)


def test_focused_passage_yields_supports_semantic_relation():
    """A concise, claim-aligned passage allows the NLI cross-encoder to recognize SUPPORTS."""
    verifier = get_semantic_verifier(mock_mode=False)

    claim = "Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969."
    focused_passage = (
        "Apollo 11 was the American spaceflight that first landed humans on the Moon. "
        "Commander Neil Armstrong and lunar module pilot Buzz Aldrin landed the Apollo Lunar Module Eagle on July 20, 1969."
    )

    pred = verifier.verify_pair(focused_passage, claim)
    assert pred.semantic_relation == SemanticRelation.SUPPORTS
    assert pred.probabilities["entailment"] > 0.60


def test_topical_entity_only_match_rejected_by_evidence_gate():
    """Evidence with entity match but zero proposition/action overlap is rejected to prevent false contradiction."""
    matcher = EvidenceMatcher()

    claim = ExtractedClaim(
        claim_id="c1",
        text="James Webb Space Telescope discovered an alien mega-structure orbiting a distant star."
    )

    unrelated_jwst_item = EvidenceItem(
        id="ref_1",
        claim_id="c1",
        source_type=EvidenceSourceType.GENERAL_REFERENCE,
        publisher="Wikipedia",
        domain="en.wikipedia.org",
        url="https://en.wikipedia.org/wiki/James_Webb_Space_Telescope",
        title="James Webb Space Telescope",
        snippet="The James Webb Space Telescope was launched on an Ariane 5 rocket from Kourou, French Guiana, and arrived at Sun-Earth L2.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, unrelated_jwst_item)
    assert match_res.relevance == RelevanceClassification.IRRELEVANT
    assert "proposition" in match_res.matching_explanation.lower() or "rejected" in match_res.matching_explanation.lower()


def test_temporal_mismatch_rejected():
    """Explicit year mismatch without action overlap is rejected."""
    matcher = EvidenceMatcher()

    claim = ExtractedClaim(
        claim_id="c1",
        text="A catastrophic earthquake struck San Francisco in 2024."
    )

    historic_item = EvidenceItem(
        id="ref_1",
        claim_id="c1",
        source_type=EvidenceSourceType.GENERAL_REFERENCE,
        publisher="Wikipedia",
        domain="en.wikipedia.org",
        url="https://en.wikipedia.org/wiki/1906_San_Francisco_earthquake",
        title="1906 San Francisco earthquake",
        snippet="The 1906 San Francisco earthquake struck the coast of Northern California on Wednesday, April 18, 1906.",
        stance=StanceType.NEUTRAL
    )

    match_res = matcher.match_evidence(claim, historic_item)
    assert match_res.relevance == RelevanceClassification.IRRELEVANT
    assert "temporal" in match_res.matching_explanation.lower() or "mismatch" in match_res.matching_explanation.lower()


def test_build_premise_text_clean_formatting():
    """build_premise_text produces clean, non-redundant premise text for all source types."""
    verifier = SemanticVerifier(mock_mode=True)

    # General reference: avoid redundant title prefix if snippet starts with title
    ref_item = EvidenceItem(
        id="ref_1",
        claim_id="c1",
        source_type=EvidenceSourceType.GENERAL_REFERENCE,
        publisher="Wikipedia",
        domain="en.wikipedia.org",
        url="https://en.wikipedia.org/wiki/Water",
        title="Water",
        snippet="Water is an inorganic compound consisting of hydrogen and oxygen.",
        stance=StanceType.NEUTRAL
    )
    premise = verifier.build_premise_text(ref_item)
    assert not premise.startswith("Water. Water is")
    assert "hydrogen and oxygen" in premise

    # Fact check: include reviewed claim and rating context
    fc_item = EvidenceItem(
        id="fc_1",
        claim_id="c1",
        source_type=EvidenceSourceType.FACT_CHECK_API,
        publisher="PolitiFact",
        domain="politifact.com",
        url="https://politifact.com/1",
        title="Fact Check Report",
        snippet="No evidence exists for this claim.",
        raw_rating="False",
        claim_reviewed="5G towers transmit respiratory viruses",
        stance=StanceType.CONTRADICTS
    )
    fc_premise = verifier.build_premise_text(fc_item)
    assert "Reviewed Claim: 5G towers transmit respiratory viruses" in fc_premise
    assert "Rating: False" in fc_premise


def test_rumor_existence_passage_evaluated_as_neutral_not_contradiction():
    """A passage merely reporting that rumors exist without factual refutation/support remains neutral."""
    verifier = get_semantic_verifier(mock_mode=False)

    claim = "5G network towers transmit respiratory viruses."
    rumor_passage = "Online rumors and social media posts circulated claiming that 5G cell towers cause illness."

    pred = verifier.verify_pair(rumor_passage, claim)
    # Merely stating rumors circulated does not logically entail or logically contradict the physical proposition
    assert pred.semantic_relation == SemanticRelation.NEUTRAL


def test_deterministic_evidence_ordering():
    """Extracting passages and processing evidence yields strictly deterministic results across runs."""
    claim = ExtractedClaim(
        claim_id="c1",
        text="Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969."
    )
    broad_extract = (
        "Apollo 11 (July 16–24, 1969) was the American spaceflight that first landed humans on the Moon. "
        "Commander Neil Armstrong and lunar module pilot Buzz Aldrin landed the Apollo Lunar Module Eagle on July 20, 1969."
    )
    p1 = extract_relevant_passage(claim, "Apollo 11", broad_extract)
    p2 = extract_relevant_passage(claim, "Apollo 11", broad_extract)
    assert p1 == p2
