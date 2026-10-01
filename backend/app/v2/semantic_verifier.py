import time
import re
import threading
from collections import OrderedDict
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType
)

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class SemanticRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"


class SemanticVerificationPrediction(BaseModel):
    premise: str
    hypothesis: str
    raw_label: str
    semantic_relation: SemanticRelation
    logits: Dict[str, float] = Field(default_factory=dict)
    probabilities: Dict[str, float] = Field(default_factory=dict)
    latency_ms: float = 0.0


class SemanticVerifierError(Exception):
    """Base exception for semantic verifier errors."""
    pass


class SemanticVerifierLoadError(SemanticVerifierError):
    """Raised when the NLI model cannot be loaded."""
    pass


class SemanticVerifier:
    """Production NLI semantic verifier for V2 claim-to-evidence reasoning.

    Uses a single cross-encoder NLI model (cross-encoder/nli-distilroberta-base) to evaluate
    whether an accepted evidence premise logically entails, contradicts, or is neutral toward a claim.
    """

    MODEL_NAME = "cross-encoder/nli-distilroberta-base"

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        mock_mode: bool = False,
        cache_max_size: int = 256
    ):
        self.model_name = model_name or self.MODEL_NAME
        self.mock_mode = mock_mode
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu") if TRANSFORMERS_AVAILABLE else "cpu"
        self.tokenizer = None
        self.model = None
        self.load_time_ms = 0.0
        self.id2label = {0: "contradiction", 1: "entailment", 2: "neutral"}
        self._prediction_cache: OrderedDict[Tuple[str, str], SemanticVerificationPrediction] = OrderedDict()
        self._cache_lock = threading.Lock()
        self._max_cache_size = cache_max_size

        if not self.mock_mode:
            self._load_model()

    def _load_model(self):
        """Loads tokenizer and sequence classification model once."""
        if not TRANSFORMERS_AVAILABLE:
            raise SemanticVerifierLoadError(
                "PyTorch and Hugging Face Transformers are required for SemanticVerifier."
            )
        try:
            start_load = time.time()
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            self.load_time_ms = (time.time() - start_load) * 1000
            if hasattr(self.model.config, "id2label") and self.model.config.id2label:
                self.id2label = self.model.config.id2label
        except Exception as e:
            raise SemanticVerifierLoadError(f"Failed to load semantic model '{self.model_name}': {str(e)}") from e

    def build_premise_text(self, item: EvidenceItem) -> str:
        """Constructs an informative premise string from an EvidenceItem based on its source type."""
        if not item:
            return ""

        title = (item.title or "").strip()
        snippet = (item.snippet or "").strip()
        claim_reviewed = (item.claim_reviewed or "").strip()
        raw_rating = (item.raw_rating or "").strip()

        if item.source_type == EvidenceSourceType.FACT_CHECK_API:
            parts = []
            if title:
                parts.append(title)
            if claim_reviewed and claim_reviewed.lower() != title.lower():
                parts.append(f"Reviewed Claim: {claim_reviewed}.")
            if raw_rating:
                parts.append(f"Rating: {raw_rating}.")
            if snippet and snippet.lower() != claim_reviewed.lower() and snippet.lower() != title.lower() and not snippet.startswith("Reviewed Claim:"):
                parts.append(snippet)
            return " ".join(parts).strip()
        elif item.source_type == EvidenceSourceType.GENERAL_REFERENCE:
            if not snippet:
                return title
            if not title:
                return snippet
            # If snippet already starts with or mentions the title cleanly, avoid redundant title prefix
            if snippet.lower().startswith(title.lower()):
                return snippet
            return f"{title}. {snippet}".strip()
        else:
            # LIVE_NEWS_SEARCH
            if not snippet:
                return title
            if not title:
                return snippet
            if snippet.lower().startswith(title.lower()):
                return snippet
            return f"{title}. {snippet}".strip()

    def clear_cache(self) -> None:
        """Clears the in-memory prediction cache."""
        with self._cache_lock:
            self._prediction_cache.clear()

    def cache_size(self) -> int:
        """Returns current number of cached predictions."""
        with self._cache_lock:
            return len(self._prediction_cache)

    def verify_pair(self, premise: str, hypothesis: str) -> SemanticVerificationPrediction:
        """Verifies semantic relation between premise (evidence text) and hypothesis (claim)."""
        premise_str = (premise or "").strip()
        hypo_str = (hypothesis or "").strip()

        if not premise_str or not hypo_str:
            return SemanticVerificationPrediction(
                premise=premise_str,
                hypothesis=hypo_str,
                raw_label="neutral",
                semantic_relation=SemanticRelation.NEUTRAL,
                logits={"contradiction": 0.0, "entailment": 0.0, "neutral": 0.0},
                probabilities={"contradiction": 0.333, "entailment": 0.333, "neutral": 0.334},
                latency_ms=0.0
            )

        # Check prediction cache under thread lock
        cache_key = (premise_str, hypo_str)
        with self._cache_lock:
            if cache_key in self._prediction_cache:
                cached_pred = self._prediction_cache[cache_key]
                self._prediction_cache.move_to_end(cache_key)
                return cached_pred.model_copy()

        if self.mock_mode or self.model is None:
            pred = SemanticVerificationPrediction(
                premise=premise_str,
                hypothesis=hypo_str,
                raw_label="neutral",
                semantic_relation=SemanticRelation.NEUTRAL,
                logits={"contradiction": 0.0, "entailment": 0.0, "neutral": 0.0},
                probabilities={"contradiction": 0.0, "entailment": 0.0, "neutral": 1.0},
                latency_ms=0.1
            )
            with self._cache_lock:
                self._prediction_cache[cache_key] = pred
                self._prediction_cache.move_to_end(cache_key)
                if len(self._prediction_cache) > self._max_cache_size:
                    self._prediction_cache.popitem(last=False)
            return pred

        start_time = time.time()

        inputs = self.tokenizer(
            premise_str,
            hypo_str,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits[0]
            probs = torch.softmax(logits, dim=-1)

        pred_idx = torch.argmax(logits).item()
        raw_label = self.id2label.get(pred_idx, "neutral").lower()

        if "entail" in raw_label:
            relation = SemanticRelation.SUPPORTS
        elif "contradict" in raw_label:
            relation = SemanticRelation.CONTRADICTS
        else:
            relation = SemanticRelation.NEUTRAL

        elapsed_ms = (time.time() - start_time) * 1000

        logits_dict = {
            self.id2label.get(i, str(i)).lower(): round(float(logits[i]), 4)
            for i in range(len(logits))
        }
        probs_dict = {
            self.id2label.get(i, str(i)).lower(): round(float(probs[i]), 4)
            for i in range(len(probs))
        }

        pred = SemanticVerificationPrediction(
            premise=premise_str,
            hypothesis=hypo_str,
            raw_label=raw_label,
            semantic_relation=relation,
            logits=logits_dict,
            probabilities=probs_dict,
            latency_ms=round(elapsed_ms, 2)
        )

        with self._cache_lock:
            self._prediction_cache[cache_key] = pred
            self._prediction_cache.move_to_end(cache_key)
            if len(self._prediction_cache) > self._max_cache_size:
                self._prediction_cache.popitem(last=False)

        return pred

    def verify_evidence_item(
        self,
        claim: ExtractedClaim,
        item: EvidenceItem
    ) -> SemanticVerificationPrediction:
        """Evaluates an EvidenceItem against an ExtractedClaim and updates the item's stance."""
        premise = self.build_premise_text(item)
        hypothesis = claim.text if claim and claim.text else ""

        pred = self.verify_pair(premise=premise, hypothesis=hypothesis)

        # Update EvidenceItem stance to reflect determination (authoritative fact-check ratings take precedence)
        if item.source_type == EvidenceSourceType.FACT_CHECK_API and item.raw_rating:
            from backend.app.v2.fact_check_retriever import determine_stance
            fc_stance = determine_stance(item.raw_rating)
            if fc_stance != StanceType.NEUTRAL:
                item.stance = fc_stance
            elif pred.semantic_relation == SemanticRelation.SUPPORTS:
                item.stance = StanceType.SUPPORTS
            elif pred.semantic_relation == SemanticRelation.CONTRADICTS:
                item.stance = StanceType.CONTRADICTS
            else:
                item.stance = StanceType.NEUTRAL
        elif pred.semantic_relation == SemanticRelation.SUPPORTS:
            item.stance = StanceType.SUPPORTS
        elif pred.semantic_relation == SemanticRelation.CONTRADICTS:
            item.stance = StanceType.CONTRADICTS
        else:
            item.stance = StanceType.NEUTRAL

        # Attach semantic diagnostic metadata
        if hasattr(item, "semantic_relation"):
            item.semantic_relation = pred.semantic_relation.value
        if hasattr(item, "semantic_probabilities"):
            item.semantic_probabilities = pred.probabilities

        return pred

    def process_claim_evidence(
        self,
        claim: ExtractedClaim,
        evidence_items: List[EvidenceItem]
    ) -> List[EvidenceItem]:
        """Applies NLI semantic verification across all accepted evidence items for a claim."""
        for item in evidence_items:
            self.verify_evidence_item(claim, item)
        return evidence_items


_semantic_verifier_instance: Optional[SemanticVerifier] = None


def get_semantic_verifier(mock_mode: bool = False) -> SemanticVerifier:
    global _semantic_verifier_instance
    if mock_mode:
        return SemanticVerifier(mock_mode=True)
    if _semantic_verifier_instance is None:
        _semantic_verifier_instance = SemanticVerifier(mock_mode=False)
    return _semantic_verifier_instance
