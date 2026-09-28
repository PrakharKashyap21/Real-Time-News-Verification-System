import pytest
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType
)
from backend.app.v2.evidence_matcher import RelevanceClassification
from backend.evaluation.semantic_verifier_prototype import SemanticRelation
from backend.evaluation.guarded_semantic_verifier import (
    GuardedSemanticVerifier,
    GuardedSemanticSummary,
    GuardedClaimVerificationResult
)


@pytest.fixture(scope="module")
def guarded_verifier():
    return GuardedSemanticVerifier()


class TestGuardedSemanticVerifier:
    """Offline unit and integration tests for GuardedSemanticVerifier."""

    def test_initialization(self, guarded_verifier):
        """Guarded verifier initializes matcher and NLI verifier."""
        assert guarded_verifier.matcher is not None
        assert guarded_verifier.nli_verifier is not None

    def test_rejected_evidence_never_invokes_nli(self, guarded_verifier):
        """Irrelevant evidence rejected by EvidenceMatcher MUST NOT invoke the NLI model."""
        claim = ExtractedClaim(
            claim_id="c_moon",
            text="Apollo 11 Astronauts Landed on Moon in July 1969"
        )
        irrelevant_item = EvidenceItem(
            id="ev_tesla",
            claim_id="c_moon",
            source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
            publisher="Financial Times",
            domain="ft.com",
            url="https://ft.com/tesla-stock",
            title="Tesla Stock Surges Following Strong Quarterly Earnings Report",
            snippet="Electric vehicle manufacturer Tesla reported record quarterly deliveries and revenue growth.",
            stance=StanceType.NEUTRAL
        )

        res = guarded_verifier.verify_claim_evidence(claim, [irrelevant_item])

        assert res.total_evidence_count == 1
        assert res.accepted_evidence_count == 0
        assert res.rejected_evidence_count == 1
        assert res.guarded_semantic_summary == GuardedSemanticSummary.NO_ACCEPTED_EVIDENCE
        assert len(res.evidence_evaluations) == 1

        eval_rec = res.evidence_evaluations[0]
        assert eval_rec.matcher_relevance == RelevanceClassification.IRRELEVANT
        assert eval_rec.nli_invoked is False
        assert eval_rec.semantic_relation is None
        assert eval_rec.probabilities == {}

    def test_accepted_evidence_invokes_nli_and_maps_relation(self, guarded_verifier):
        """Relevant evidence accepted by EvidenceMatcher invokes NLI and maps stance."""
        claim = ExtractedClaim(
            claim_id="c_paris",
            text="Paris Agreement on Climate Change Adopted by International Consensus"
        )
        relevant_item = EvidenceItem(
            id="ev_paris",
            claim_id="c_paris",
            source_type=EvidenceSourceType.GENERAL_REFERENCE,
            publisher="Wikipedia",
            domain="en.wikipedia.org",
            url="https://en.wikipedia.org/wiki/Paris_Agreement",
            title="Paris Agreement",
            snippet="The Paris Agreement is an international treaty on climate change adopted by international consensus in 2015 and signed in 2016.",
            stance=StanceType.NEUTRAL
        )

        res = guarded_verifier.verify_claim_evidence(claim, [relevant_item])

        assert res.total_evidence_count == 1
        assert res.accepted_evidence_count == 1
        assert res.rejected_evidence_count == 0
        assert res.supports_count == 1
        assert res.guarded_semantic_summary == GuardedSemanticSummary.ALL_SUPPORTS

        eval_rec = res.evidence_evaluations[0]
        assert eval_rec.matcher_relevance == RelevanceClassification.RELEVANT
        assert eval_rec.nli_invoked is True
        assert eval_rec.semantic_relation == SemanticRelation.SUPPORTS
        assert "entailment" in eval_rec.probabilities

    def test_direct_support_recognition(self, guarded_verifier):
        """Verifies direct support recognition for Apollo 11 historical claim."""
        claim = ExtractedClaim(
            claim_id="c_apollo",
            text="Apollo 11 Astronauts Landed on Moon in July 1969"
        )
        apollo_item = EvidenceItem(
            id="ev_apollo",
            claim_id="c_apollo",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="Reuters",
            domain="reuters.com",
            url="https://reuters.com/factcheck/apollo",
            title="Fact check: Apollo 11 moon landing was not staged in Hollywood",
            snippet="Claim: The Apollo 11 moon landing was staged and faked. Rating: False. Neil Armstrong and Buzz Aldrin landed the Apollo 11 Lunar Module on the Moon on July 20, 1969.",
            stance=StanceType.CONTRADICTS
        )

        res = guarded_verifier.verify_claim_evidence(claim, [apollo_item])
        assert res.accepted_evidence_count == 1
        assert res.supports_count == 1
        assert res.guarded_semantic_summary == GuardedSemanticSummary.ALL_SUPPORTS

    def test_direct_contradiction_recognition(self, guarded_verifier):
        """Verifies direct contradiction recognition for 5G microchip conspiracy."""
        claim = ExtractedClaim(
            claim_id="c_5g",
            text="COVID-19 Vaccines Contain Injectable 5G Microchips for Digital Surveillance"
        )
        contra_item = EvidenceItem(
            id="ev_5g",
            claim_id="c_5g",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="AFP Fact Check",
            domain="factcheck.afp.com",
            url="https://factcheck.afp.com/5g-chips",
            title="Fact check: COVID-19 vaccines do not contain injectable 5G microchips",
            snippet="Public health agencies confirm COVID-19 vaccines contain mRNA or viral vectors without microchips, 5G tracking hardware, or electronic surveillance devices.",
            stance=StanceType.CONTRADICTS
        )

        res = guarded_verifier.verify_claim_evidence(claim, [contra_item])
        assert res.accepted_evidence_count == 1
        assert res.contradicts_count == 1
        assert res.guarded_semantic_summary == GuardedSemanticSummary.ALL_CONTRADICTS

    def test_adjacent_crispr_neutral_resolution(self, guarded_verifier):
        """Verifies that an adjacent vaccine CRISPR debunk resolves to NEUTRAL for Charpentier development claim."""
        claim = ExtractedClaim(
            claim_id="c_crispr",
            text="CRISPR-Cas9 gene editing technology was developed by Emmanuelle Charpentier and Jennifer Doudna"
        )
        crispr_vax_item = EvidenceItem(
            id="ev_crispr_vax",
            claim_id="c_crispr",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="Full Fact",
            domain="fullfact.org",
            url="https://fullfact.org/crispr-vaccine",
            title="Fact check: COVID-19 mRNA vaccines do not contain CRISPR-Cas9 gene editing tools",
            snippet="Claim: COVID-19 vaccines alter human DNA using CRISPR gene editing. Rating: False.",
            stance=StanceType.CONTRADICTS
        )

        res = guarded_verifier.verify_claim_evidence(claim, [crispr_vax_item])
        assert res.accepted_evidence_count == 1
        assert res.neutral_count == 1
        assert res.guarded_semantic_summary == GuardedSemanticSummary.ONLY_NEUTRAL

    def test_multi_evidence_aggregation_behavior(self, guarded_verifier):
        """Tests deterministic multi-evidence aggregation for mixed support and neutral items."""
        claim = ExtractedClaim(
            claim_id="c_multi",
            text="European Union Bans Internal Combustion Engine Cars by 2035"
        )
        supp_item = EvidenceItem(
            id="ev_supp",
            claim_id="c_multi",
            source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
            publisher="Full Fact",
            domain="fullfact.org",
            url="https://fullfact.org/eu-cars",
            title="European Parliament votes to end sales of new petrol and diesel cars from 2035",
            snippet="The European Parliament approved legislation mandating zero emissions for new cars, banning new internal combustion engine cars from 2035.",
            stance=StanceType.SUPPORTS
        )
        neut_item = EvidenceItem(
            id="ev_neut",
            claim_id="c_multi",
            source_type=EvidenceSourceType.GENERAL_REFERENCE,
            publisher="Wikipedia",
            domain="en.wikipedia.org",
            url="https://en.wikipedia.org/wiki/European_Union",
            title="European Union",
            snippet="The European Union is a political and economic union of 27 member states that are located primarily in Europe.",
            stance=StanceType.NEUTRAL
        )
        irrel_item = EvidenceItem(
            id="ev_irrel",
            claim_id="c_multi",
            source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
            publisher="BBC",
            domain="bbc.com",
            url="https://bbc.com/aviation",
            title="Commercial Aviation Sector Announces Net Zero Roadmap",
            snippet="Airlines outlined long-term plans to adopt sustainable aviation fuel.",
            stance=StanceType.NEUTRAL
        )

        res = guarded_verifier.verify_claim_evidence(claim, [supp_item, neut_item, irrel_item])
        assert res.total_evidence_count == 3
        assert res.rejected_evidence_count == 1
        assert res.accepted_evidence_count == 2
        assert res.supports_count == 1
        assert res.neutral_count == 1
        assert res.guarded_semantic_summary == GuardedSemanticSummary.SUPPORTS_WITH_NEUTRAL

    def test_empty_evidence_list_handling(self, guarded_verifier):
        """Empty evidence list safely returns NO_ACCEPTED_EVIDENCE without invoking NLI."""
        claim = ExtractedClaim(claim_id="c_none", text="Some Claim Assertion")
        res = guarded_verifier.verify_claim_evidence(claim, [])
        assert res.total_evidence_count == 0
        assert res.accepted_evidence_count == 0
        assert res.guarded_semantic_summary == GuardedSemanticSummary.NO_ACCEPTED_EVIDENCE
