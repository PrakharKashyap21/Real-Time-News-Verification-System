import pytest
from backend.evaluation.semantic_verifier_prototype import (
    SemanticVerifierPrototype,
    SemanticRelation,
    SemanticVerificationPrediction,
    CONTROLLED_TEST_SET
)


@pytest.fixture(scope="module")
def verifier():
    return SemanticVerifierPrototype()


class TestSemanticVerifierPrototype:
    """Offline unit tests for SemanticVerifierPrototype."""

    def test_model_initialization(self, verifier):
        """Verifier loads successfully with configured labels and model name."""
        assert verifier is not None
        assert verifier.model_name == "cross-encoder/nli-distilroberta-base"
        assert verifier.load_time_ms > 0
        assert 0 in verifier.id2label
        assert 1 in verifier.id2label
        assert 2 in verifier.id2label

    def test_empty_input_handling(self, verifier):
        """Empty premise or hypothesis safely returns NEUTRAL without crashing."""
        res1 = verifier.verify_pair("", "Some claim")
        assert res1.semantic_relation == SemanticRelation.NEUTRAL

        res2 = verifier.verify_pair("Some evidence", "")
        assert res2.semantic_relation == SemanticRelation.NEUTRAL

        res3 = verifier.verify_pair(None, None)
        assert res3.semantic_relation == SemanticRelation.NEUTRAL

    def test_deterministic_output_contract(self, verifier):
        """Output prediction contains properly formatted relation, logits, probabilities, and latency."""
        premise = "Water is composed of hydrogen and oxygen atoms."
        hypothesis = "Water molecules contain hydrogen and oxygen."
        pred = verifier.verify_pair(premise, hypothesis)

        assert isinstance(pred, SemanticVerificationPrediction)
        assert pred.semantic_relation in (SemanticRelation.SUPPORTS, SemanticRelation.CONTRADICTS, SemanticRelation.NEUTRAL)
        assert "entailment" in pred.probabilities
        assert "contradiction" in pred.probabilities
        assert "neutral" in pred.probabilities
        assert abs(sum(pred.probabilities.values()) - 1.0) < 0.01
        assert pred.latency_ms > 0

    def test_clear_support_entailment(self, verifier):
        """Direct premise entails hypothesis as SUPPORTS."""
        premise = "The Paris Agreement is an international treaty on climate change adopted by international consensus."
        hypothesis = "Paris Agreement on Climate Change Adopted by International Consensus"
        pred = verifier.verify_pair(premise, hypothesis)
        assert pred.semantic_relation == SemanticRelation.SUPPORTS
        assert pred.raw_label == "entailment"

    def test_clear_contradiction(self, verifier):
        """Direct counter-evidence contradicts hypothesis as CONTRADICTS."""
        premise = "The European Union has never passed any directive or legislation requiring citizens to receive RFID microchip implants."
        hypothesis = "European Union Passes Emergency Law Mandating RFID Microchip Implants"
        pred = verifier.verify_pair(premise, hypothesis)
        assert pred.semantic_relation == SemanticRelation.CONTRADICTS
        assert pred.raw_label == "contradiction"

    def test_clear_neutral_unrelated(self, verifier):
        """Topical background text without proposition confirmation remains NEUTRAL."""
        premise = "Calvin Coolidge served as the 30th President of the United States from 1923 to 1929."
        hypothesis = "Coin Collector Claims Finding 1923 Silver Dollar Hand-Signed by President Coolidge"
        pred = verifier.verify_pair(premise, hypothesis)
        assert pred.semantic_relation == SemanticRelation.NEUTRAL

    def test_controlled_test_set_execution(self, verifier):
        """Controlled 24-case test set executes cleanly with bounded latency."""
        assert len(CONTROLLED_TEST_SET) == 24
        predictions = []
        for case in CONTROLLED_TEST_SET:
            p = case["premise"]
            h = case["hypothesis"]
            res = verifier.verify_pair(p, h)
            predictions.append(res)

        assert len(predictions) == 24
        # Assert average per-pair latency is bounded (< 100ms on CPU)
        avg_latency = sum(r.latency_ms for r in predictions) / len(predictions)
        assert avg_latency < 100.0
