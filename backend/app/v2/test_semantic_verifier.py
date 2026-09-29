import pytest
from unittest.mock import MagicMock, patch
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType,
    ClaimVerdict,
    EvidenceStrength,
    UncertaintyLevel,
    VerificationRequest
)
from backend.app.v2.semantic_verifier import (
    SemanticVerifier,
    SemanticRelation,
    SemanticVerificationPrediction,
    SemanticVerifierLoadError,
    get_semantic_verifier
)
from backend.app.v2.evidence_matcher import EvidenceMatcher, RelevanceClassification
from backend.app.v2.evidence_aggregator import EvidenceAggregator
from backend.app.v2.verdict_engine import VerdictEngine
from backend.app.v2.svm_signal import SVMPipelineIntegrator, SVMSignalProvider
from backend.app.v2.verification_service import VerificationService


@pytest.fixture(scope="module")
def semantic_verifier():
    return get_semantic_verifier()


class TestSemanticVerifierUnit:
    """Unit tests for the production SemanticVerifier module."""

    def test_singleton_initialization(self, semantic_verifier):
        """Model loads once as a singleton with correct configuration."""
        assert semantic_verifier is not None
        assert semantic_verifier.model_name == "cross-encoder/nli-distilroberta-base"
        assert semantic_verifier.model is not None
        assert semantic_verifier.tokenizer is not None

    def test_direct_support_inference(self, semantic_verifier):
        """Premise entailing hypothesis produces SUPPORTS relation."""
        premise = "The Paris Agreement is a legally binding international treaty on climate change adopted in 2015."
        hypothesis = "Paris Agreement on Climate Change Adopted by International Consensus"
        pred = semantic_verifier.verify_pair(premise, hypothesis)

        assert pred.semantic_relation == SemanticRelation.SUPPORTS
        assert pred.probabilities["entailment"] > 0.5

    def test_direct_contradiction_inference(self, semantic_verifier):
        """Premise contradicting hypothesis produces CONTRADICTS relation."""
        premise = "Fact Check: Public health agencies confirm COVID-19 vaccines do not contain injectable 5G microchips."
        hypothesis = "COVID-19 Vaccines Contain Injectable 5G Microchips for Digital Surveillance"
        pred = semantic_verifier.verify_pair(premise, hypothesis)

        assert pred.semantic_relation == SemanticRelation.CONTRADICTS
        assert pred.probabilities["contradiction"] > 0.5

    def test_neutral_unrelated_inference(self, semantic_verifier):
        """Topically related but non-entailing premise produces NEUTRAL relation."""
        premise = "Calvin Coolidge served as the 30th President of the United States from 1923 to 1929 and oversaw a period of rapid economic growth."
        hypothesis = "Coin Collector Claims Finding 1923 Silver Dollar Hand-Signed by President Coolidge"
        pred = semantic_verifier.verify_pair(premise, hypothesis)

        assert pred.semantic_relation == SemanticRelation.NEUTRAL
        assert pred.probabilities["neutral"] > 0.5

    def test_evidence_with_claim_reviewed_premise_building(self, semantic_verifier):
        """Builds structured premise using claim_reviewed, raw_rating, and title."""
        item = EvidenceItem(
            id="ev_fc_1",
            claim_id="c_1",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="FactCheck.org",
            domain="factcheck.org",
            url="https://factcheck.org/lemon-cancer",
            title="Hot lemon water does not cure cancer",
            claim_reviewed="Hot lemon water destroys cancer cells and cures all cancer",
            raw_rating="False",
            snippet="Drinking lemon water cannot replace cancer therapy.",
            stance=StanceType.NEUTRAL
        )
        premise = semantic_verifier.build_premise_text(item)
        assert "Reviewed Claim: Hot lemon water destroys cancer cells" in premise
        assert "Rating: False" in premise

        claim = ExtractedClaim(claim_id="c_1", text="Drinking hot lemon water cures all cancer completely")
        pred = semantic_verifier.verify_evidence_item(claim, item)
        assert item.stance == StanceType.CONTRADICTS
        assert pred.semantic_relation == SemanticRelation.CONTRADICTS

    def test_general_reference_evidence_verification(self, semantic_verifier):
        """General reference extract entailing claim updates stance to SUPPORTS."""
        claim = ExtractedClaim(
            claim_id="c_water",
            text="Water molecule chemical composition consists of hydrogen and oxygen"
        )
        ref_item = EvidenceItem(
            id="ev_ref_water",
            claim_id="c_water",
            source_type=EvidenceSourceType.GENERAL_REFERENCE,
            publisher="Wikipedia",
            domain="en.wikipedia.org",
            url="https://en.wikipedia.org/wiki/Molecule",
            title="Molecule",
            snippet="Water is a chemical compound consisting of two hydrogen atoms and one oxygen atom (H2O).",
            stance=StanceType.NEUTRAL
        )

        semantic_verifier.verify_evidence_item(claim, ref_item)
        assert ref_item.stance == StanceType.SUPPORTS
        assert ref_item.semantic_relation == "SUPPORTS"

    def test_newsapi_evidence_verification(self, semantic_verifier):
        """Live news report entailing claim updates stance to SUPPORTS."""
        claim = ExtractedClaim(
            claim_id="c_eu",
            text="European Union Bans Internal Combustion Engine Cars by 2035"
        )
        news_item = EvidenceItem(
            id="ev_news_eu",
            claim_id="c_eu",
            source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
            publisher="Reuters",
            domain="reuters.com",
            url="https://reuters.com/eu-cars",
            title="EU approves 2035 phaseout for new combustion engine vehicles",
            snippet="The European Union has approved legislation mandating zero emissions for new cars, banning new internal combustion engine cars from 2035.",
            stance=StanceType.NEUTRAL
        )

        semantic_verifier.verify_evidence_item(claim, news_item)
        assert news_item.stance == StanceType.SUPPORTS

    def test_empty_and_whitespace_input_handling(self, semantic_verifier):
        """Empty or whitespace input safely defaults to NEUTRAL without exception."""
        pred = semantic_verifier.verify_pair("", "")
        assert pred.semantic_relation == SemanticRelation.NEUTRAL
        assert pred.latency_ms == 0.0

    def test_model_load_failure_handling(self):
        """Simulated model loading failure raises explicit SemanticVerifierLoadError."""
        with patch("transformers.AutoTokenizer.from_pretrained", side_effect=RuntimeError("Download failed")):
            with pytest.raises(SemanticVerifierLoadError):
                SemanticVerifier(model_name="invalid-model-path", mock_mode=False)


class TestSemanticPipelineIntegration:
    """Integration tests verifying full V2 pipeline from retrieval to verdict."""

    def test_pipeline_single_supporting_fact_check(self, semantic_verifier):
        """Full mocked flow: supporting fact check -> matcher -> semantic verifier -> SUPPORTED."""
        claim = ExtractedClaim(claim_id="c_apollo", text="Apollo 11 Astronauts Landed on Moon in July 1969")
        apollo_item = EvidenceItem(
            id="ev_apollo",
            claim_id="c_apollo",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="Reuters",
            domain="reuters.com",
            url="https://reuters.com/factcheck/apollo",
            title="Fact check: Apollo 11 moon landing was not staged in Hollywood",
            snippet="Claim: The Apollo 11 moon landing was staged and faked. Rating: False. Neil Armstrong and Buzz Aldrin landed the Apollo 11 Lunar Module on the Moon on July 20, 1969.",
            stance=StanceType.NEUTRAL
        )

        matcher = EvidenceMatcher()
        aggregator = EvidenceAggregator()
        verdict_engine = VerdictEngine(aggregator=aggregator)

        # 1. Gate
        matched = matcher.process_claim_evidence(claim, [apollo_item])
        assert len(matched) == 1

        # 2. Semantic Verifier
        verified = semantic_verifier.process_claim_evidence(claim, matched)
        assert verified[0].stance == StanceType.SUPPORTS

        # 3. Aggregation & Verdict
        summary = aggregator.aggregate_evidence(claim, verified)
        res = verdict_engine.verify_summary(summary)

        assert res.verdict == ClaimVerdict.SUPPORTED
        assert res.supporting_evidence_count == 1
        assert res.contradicting_evidence_count == 0
        assert res.semantic_relation == "SUPPORTS"

    def test_pipeline_adjacent_hoax_rejected_at_gate(self, semantic_verifier):
        """Adjacent hoax is rejected at matcher gate and NEVER reaches semantic verifier."""
        claim = ExtractedClaim(
            claim_id="c_jwst",
            text="James Webb Space Telescope Unveils Deepest Infrared Image of Universe"
        )
        jwst_hoax = EvidenceItem(
            id="ev_jwst_chorizo",
            claim_id="c_jwst",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="USA Today",
            domain="usatoday.com",
            url="https://usatoday.com/factcheck/chorizo",
            title="Fact check: Photo shows a slice of chorizo sausage, not a star from James Webb Space Telescope",
            snippet="Claim: Photo shows a star captured by James Webb Space Telescope. Rating: False.",
            stance=StanceType.NEUTRAL
        )

        matcher = EvidenceMatcher()
        aggregator = EvidenceAggregator()
        verdict_engine = VerdictEngine(aggregator=aggregator)

        # 1. Gate: must reject
        matched = matcher.process_claim_evidence(claim, [jwst_hoax])
        assert len(matched) == 0

        # 2. Semantic Verifier on accepted only
        verified = semantic_verifier.process_claim_evidence(claim, matched)
        assert len(verified) == 0

        # 3. Verdict: UNVERIFIED (conservative)
        summary = aggregator.aggregate_evidence(claim, verified)
        res = verdict_engine.verify_summary(summary)

        assert res.verdict == ClaimVerdict.UNVERIFIED
        assert res.supporting_evidence_count == 0
        assert res.contradicting_evidence_count == 0

    def test_pipeline_temporal_mismatch_rejected_at_gate(self, semantic_verifier):
        """Distinct year event mismatch is rejected at matcher gate and produces UNVERIFIED."""
        claim = ExtractedClaim(
            claim_id="c_voyager",
            text="NASA Voyager 1 Reached Interstellar Space in August 2012"
        )
        glitch_item = EvidenceItem(
            id="ev_voyager_glitch",
            claim_id="c_voyager",
            source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
            publisher="SpaceNews",
            domain="spacenews.com",
            url="https://spacenews.com/voyager-2024",
            title="Voyager 1 resumes sending telemetry in 2024 after engineers resolve chip glitch",
            snippet="Engineers restored data transmissions from Voyager 1 in 2024.",
            stance=StanceType.NEUTRAL
        )

        matcher = EvidenceMatcher()
        aggregator = EvidenceAggregator()
        verdict_engine = VerdictEngine(aggregator=aggregator)

        matched = matcher.process_claim_evidence(claim, [glitch_item])
        assert len(matched) == 0

        verified = semantic_verifier.process_claim_evidence(claim, matched)
        summary = aggregator.aggregate_evidence(claim, verified)
        res = verdict_engine.verify_summary(summary)

        assert res.verdict == ClaimVerdict.UNVERIFIED

    def test_pipeline_conflict_state(self, semantic_verifier):
        """Mixed supporting and contradicting evidence produces conflict UNVERIFIED state."""
        claim = ExtractedClaim(claim_id="c_mixed", text="Electric vehicles reduce overall greenhouse gas emissions")
        supp_item = EvidenceItem(
            id="ev_s",
            claim_id="c_mixed",
            source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
            publisher="EPA",
            domain="epa.gov",
            url="https://epa.gov/ev",
            title="Electric vehicles emit fewer greenhouse gases over lifetime than gas cars",
            snippet="Comprehensive lifecycle analysis confirms electric vehicles reduce net greenhouse gas emissions.",
            stance=StanceType.NEUTRAL
        )
        contra_item = EvidenceItem(
            id="ev_c",
            claim_id="c_mixed",
            source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
            publisher="Blog",
            domain="blog.com",
            url="https://blog.com/ev-myth",
            title="Study claims electric vehicles do not reduce greenhouse gas emissions",
            snippet="Report disputes that electric vehicles reduce overall greenhouse gas emissions.",
            stance=StanceType.NEUTRAL
        )

        matcher = EvidenceMatcher()
        aggregator = EvidenceAggregator()
        verdict_engine = VerdictEngine(aggregator=aggregator)

        matched = matcher.process_claim_evidence(claim, [supp_item, contra_item])
        verified = semantic_verifier.process_claim_evidence(claim, matched)
        summary = aggregator.aggregate_evidence(claim, verified)
        res = verdict_engine.verify_summary(summary)

        assert res.has_conflicting_evidence is True
        assert res.verdict == ClaimVerdict.UNVERIFIED
        assert res.semantic_relation == "CONFLICT"

    def test_svm_does_not_override_semantic_verdict(self, semantic_verifier):
        """Linguistic SVM signal cannot override or mutate semantic verdict."""
        claim = ExtractedClaim(claim_id="c_5g", text="COVID-19 Vaccines Contain Injectable 5G Microchips")
        contra_item = EvidenceItem(
            id="ev_5g",
            claim_id="c_5g",
            source_type=EvidenceSourceType.FACT_CHECK_API,
            publisher="AFP",
            domain="afp.com",
            url="https://afp.com/5g",
            title="Fact check: COVID-19 vaccines do not contain injectable 5G microchips",
            snippet="Public health agencies confirm vaccines contain no microchips or 5G devices.",
            stance=StanceType.NEUTRAL
        )

        matcher = EvidenceMatcher()
        aggregator = EvidenceAggregator()
        verdict_engine = VerdictEngine(aggregator=aggregator)

        matched = matcher.process_claim_evidence(claim, [contra_item])
        verified = semantic_verifier.process_claim_evidence(claim, matched)
        summary = aggregator.aggregate_evidence(claim, verified)
        base_res = verdict_engine.verify_summary(summary)

        assert base_res.verdict == ClaimVerdict.CONTRADICTED

        # Mock SVM returning 'Real News' (label 1, high confidence)
        mock_svm = MagicMock(spec=SVMSignalProvider)
        from backend.app.v2.schemas import LinguisticSignal
        mock_svm.get_signal_for_claim.return_value = LinguisticSignal(
            label=1, prediction="REAL", confidence=0.99, message="Real news patterns"
        )
        integrator = SVMPipelineIntegrator(svm_provider=mock_svm)
        res_with_svm = integrator.attach_signal_to_result(claim, base_res)

        # Verdict remains CONTRADICTED despite SVM prediction
        assert res_with_svm.verdict == ClaimVerdict.CONTRADICTED
        assert res_with_svm.semantic_relation == "CONTRADICTS"
        assert res_with_svm.linguistic_signal.prediction == "REAL"
