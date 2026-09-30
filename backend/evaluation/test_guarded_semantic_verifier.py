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
    """Offline unit and regression tests for GuardedSemanticVerifier (Stage 34E Gate Refinements)."""

    def test_initialization(self, guarded_verifier):
        """Guarded verifier initializes matcher and NLI verifier."""
        assert guarded_verifier.matcher is not None
        assert guarded_verifier.nli_verifier is not None

    def test_unrelated_entity_topic_rejected(self, guarded_verifier):
        """Regression 7: Unrelated entity/topic must be rejected and never invoke NLI."""
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

    def test_water_composition_evidence_survives_gate(self, guarded_verifier):
        """Regression 1: Valid water composition reference evidence must survive the relevance gate and be verified."""
        claim = ExtractedClaim(
            claim_id="real_05",
            text="Water molecule consists of two hydrogen atoms bonded to one oxygen atom"
        )
        water_item = EvidenceItem(
            id="ev_water_wiki",
            claim_id="real_05",
            source_type=EvidenceSourceType.GENERAL_REFERENCE,
            publisher="Wikipedia",
            domain="en.wikipedia.org",
            url="https://en.wikipedia.org/wiki/Molecule",
            title="Molecule",
            snippet="Water is a chemical compound consisting of two hydrogen atoms and one oxygen atom (H2O).",
            stance=StanceType.NEUTRAL
        )

        res = guarded_verifier.verify_claim_evidence(claim, [water_item])

        assert res.total_evidence_count == 1
        assert res.accepted_evidence_count == 1
        assert res.rejected_evidence_count == 0
        assert res.supports_count == 1
        assert res.guarded_semantic_summary == GuardedSemanticSummary.ALL_SUPPORTS

        eval_rec = res.evidence_evaluations[0]
        assert eval_rec.matcher_relevance == RelevanceClassification.RELEVANT
        assert eval_rec.nli_invoked is True
        assert eval_rec.semantic_relation == SemanticRelation.SUPPORTS

    def test_jwst_adjacent_hoax_prevented_from_contradiction(self, guarded_verifier):
        """Regression 2: JWST adjacent hoax must be rejected or prevented from reaching NLI as direct contradiction."""
        claim = ExtractedClaim(
            claim_id="real_02",
            text="James Webb Space Telescope captures deepest infrared image of early universe"
        )
        jwst_hoax_item = EvidenceItem(
            id="ev_jwst_hoax",
            claim_id="real_02",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="Full Fact",
            domain="fullfact.org",
            url="https://fullfact.org/jwst-chorizo",
            title="Fact check: French scientist did not discover new star with James Webb telescope; image was slice of chorizo sausage",
            snippet="Claim: Scientist discovered distant star using James Webb telescope. Rating: False.",
            stance=StanceType.CONTRADICTS
        )

        res = guarded_verifier.verify_claim_evidence(claim, [jwst_hoax_item])

        assert res.contradicts_count == 0
        assert res.guarded_semantic_summary != GuardedSemanticSummary.ALL_CONTRADICTS
        # Filtered at gate as IRRELEVANT adjacent fact-check
        assert res.accepted_evidence_count == 0
        assert res.rejected_evidence_count == 1

    def test_voyager_temporal_mismatch_prevented_from_contradiction(self, guarded_verifier):
        """Regression 3: Voyager 2012 vs 2024 temporal event mismatch must be filtered and not produce contradiction."""
        claim = ExtractedClaim(
            claim_id="real_01",
            text="Voyager 1 spacecraft resumes sending science data to Earth after communications glitch in 2024"
        )
        voyager_old_item = EvidenceItem(
            id="ev_voyager_2012",
            claim_id="real_01",
            source_type=EvidenceSourceType.GENERAL_REFERENCE,
            publisher="Wikipedia",
            domain="en.wikipedia.org",
            url="https://en.wikipedia.org/wiki/Voyager_1",
            title="Voyager 1",
            snippet="Voyager 1 crossed the heliopause and entered interstellar space in August 2012.",
            stance=StanceType.NEUTRAL
        )

        res = guarded_verifier.verify_claim_evidence(claim, [voyager_old_item])

        assert res.contradicts_count == 0
        assert res.accepted_evidence_count == 0
        assert res.rejected_evidence_count == 1
        assert res.guarded_semantic_summary == GuardedSemanticSummary.NO_ACCEPTED_EVIDENCE

    def test_apollo_direct_historical_evidence_survives(self, guarded_verifier):
        """Regression 4: Apollo 11 direct historical fact-check debunking staged hoax must survive and support."""
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

    def test_5g_microchip_direct_contradiction_survives(self, guarded_verifier):
        """Regression 5: 5G microchip conspiracy fact-check must survive and contradict."""
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

    def test_crispr_adjacent_vaccine_debunk_not_contradiction(self, guarded_verifier):
        """Regression 6: Adjacent CRISPR vaccine debunk must remain neutral/irrelevant rather than becoming contradiction."""
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
        # Must NOT contradict the true development claim
        assert res.contradicts_count == 0
        assert res.guarded_semantic_summary in (
            GuardedSemanticSummary.NO_ACCEPTED_EVIDENCE,
            GuardedSemanticSummary.ONLY_NEUTRAL
        )

    def test_fact_check_claim_reviewed_exact_match_survives(self, guarded_verifier):
        """Regression 8: Existing fact-check with exact/near-exact claimReviewed alignment must survive."""
        claim = ExtractedClaim(
            claim_id="c_lemon",
            text="Drinking hot lemon water cures all types of cancer completely"
        )
        fc_item = EvidenceItem(
            id="ev_fc_lemon",
            claim_id="c_lemon",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="FactCheck.org",
            domain="factcheck.org",
            url="https://factcheck.org/lemon-cancer",
            title="Fact check: Hot lemon water does not cure cancer",
            claim_reviewed="Hot lemon water destroys cancer cells and cures all cancer",
            snippet="Reviewed Claim: Hot lemon water destroys cancer cells and cures all cancer | Rating: False",
            stance=StanceType.CONTRADICTS
        )

        res = guarded_verifier.verify_claim_evidence(claim, [fc_item])
        assert res.accepted_evidence_count == 1
        assert res.contradicts_count == 1
        assert res.guarded_semantic_summary == GuardedSemanticSummary.ALL_CONTRADICTS

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
            snippet="European Union regulations on cars and transport guide environmental policies across member states.",
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
