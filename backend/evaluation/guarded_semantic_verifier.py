import time
from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

from backend.app.v2.schemas import ExtractedClaim, EvidenceItem, EvidenceSourceType
from backend.app.v2.evidence_matcher import get_evidence_matcher, EvidenceMatcher, RelevanceClassification
from backend.evaluation.semantic_verifier_prototype import (
    SemanticVerifierPrototype,
    SemanticRelation,
    SemanticVerificationPrediction
)


class GuardedEvidenceEvaluation(BaseModel):
    """Evaluation record for an individual evidence item passing through EvidenceMatcher and NLI."""
    evidence_id: str
    claim_id: str
    matcher_relevance: RelevanceClassification
    matcher_explanation: str
    nli_invoked: bool
    nli_raw_label: Optional[str] = None
    semantic_relation: Optional[SemanticRelation] = None
    probabilities: Dict[str, float] = Field(default_factory=dict)
    logits: Dict[str, float] = Field(default_factory=dict)
    latency_ms: float = 0.0


class GuardedSemanticSummary(str, Enum):
    ALL_SUPPORTS = "ALL_SUPPORTS"
    ALL_CONTRADICTS = "ALL_CONTRADICTS"
    MIXED_SUPPORT_CONTRADICT = "MIXED_SUPPORT_CONTRADICT"
    SUPPORTS_WITH_NEUTRAL = "SUPPORTS_WITH_NEUTRAL"
    CONTRADICTS_WITH_NEUTRAL = "CONTRADICTS_WITH_NEUTRAL"
    ONLY_NEUTRAL = "ONLY_NEUTRAL"
    NO_ACCEPTED_EVIDENCE = "NO_ACCEPTED_EVIDENCE"


class GuardedClaimVerificationResult(BaseModel):
    """Guarded semantic verification result for an extracted claim across its candidate evidence."""
    claim_id: str
    claim_text: str
    total_evidence_count: int = 0
    accepted_evidence_count: int = 0
    rejected_evidence_count: int = 0
    supports_count: int = 0
    contradicts_count: int = 0
    neutral_count: int = 0
    guarded_semantic_summary: GuardedSemanticSummary
    evidence_evaluations: List[GuardedEvidenceEvaluation] = Field(default_factory=list)


class GuardedSemanticVerifier:
    """Guarded Semantic Verification prototype orchestrating EvidenceMatcher guardrails with NLI verification.

    Workflow:
      Claim -> EvidenceMatcher Filter -> Only Accepted Evidence -> NLI Cross-Encoder -> Deterministic Stance Mapping.
    Rejected evidence is NEVER evaluated by the NLI model.
    """

    def __init__(
        self,
        matcher: Optional[EvidenceMatcher] = None,
        nli_verifier: Optional[SemanticVerifierPrototype] = None
    ):
        self.matcher = matcher or get_evidence_matcher()
        self.nli_verifier = nli_verifier or SemanticVerifierPrototype()

    def verify_claim_evidence(
        self,
        claim: ExtractedClaim,
        evidence_items: List[EvidenceItem]
    ) -> GuardedClaimVerificationResult:
        """Processes candidate evidence items through EvidenceMatcher and runs NLI strictly on accepted items."""
        claim_id = claim.claim_id if claim and claim.claim_id else "unknown_claim"
        claim_text = claim.text if claim and claim.text else ""

        if not evidence_items:
            return GuardedClaimVerificationResult(
                claim_id=claim_id,
                claim_text=claim_text,
                total_evidence_count=0,
                accepted_evidence_count=0,
                rejected_evidence_count=0,
                supports_count=0,
                contradicts_count=0,
                neutral_count=0,
                guarded_semantic_summary=GuardedSemanticSummary.NO_ACCEPTED_EVIDENCE,
                evidence_evaluations=[]
            )

        evaluations: List[GuardedEvidenceEvaluation] = []
        accepted_count = 0
        rejected_count = 0
        supports_count = 0
        contradicts_count = 0
        neutral_count = 0

        for item in evidence_items:
            match_res = self.matcher.match_evidence(claim, item)

            if match_res.relevance == RelevanceClassification.IRRELEVANT:
                rejected_count += 1
                evaluations.append(
                    GuardedEvidenceEvaluation(
                        evidence_id=item.id,
                        claim_id=claim_id,
                        matcher_relevance=RelevanceClassification.IRRELEVANT,
                        matcher_explanation=match_res.matching_explanation,
                        nli_invoked=False,
                        nli_raw_label=None,
                        semantic_relation=None,
                        probabilities={},
                        logits={},
                        latency_ms=0.0
                    )
                )
            else:
                accepted_count += 1
                premise_text = f"{item.title or ''}. {item.snippet or ''}".strip()
                hypothesis_text = claim_text.strip()

                nli_pred: SemanticVerificationPrediction = self.nli_verifier.verify_pair(
                    premise=premise_text,
                    hypothesis=hypothesis_text
                )

                if nli_pred.semantic_relation == SemanticRelation.SUPPORTS:
                    supports_count += 1
                elif nli_pred.semantic_relation == SemanticRelation.CONTRADICTS:
                    contradicts_count += 1
                else:
                    neutral_count += 1

                evaluations.append(
                    GuardedEvidenceEvaluation(
                        evidence_id=item.id,
                        claim_id=claim_id,
                        matcher_relevance=RelevanceClassification.RELEVANT,
                        matcher_explanation=match_res.matching_explanation,
                        nli_invoked=True,
                        nli_raw_label=nli_pred.raw_label,
                        semantic_relation=nli_pred.semantic_relation,
                        probabilities=nli_pred.probabilities,
                        logits=nli_pred.logits,
                        latency_ms=nli_pred.latency_ms
                    )
                )

        # Deterministic multi-evidence summary aggregation
        if accepted_count == 0:
            summary = GuardedSemanticSummary.NO_ACCEPTED_EVIDENCE
        elif supports_count > 0 and contradicts_count > 0:
            summary = GuardedSemanticSummary.MIXED_SUPPORT_CONTRADICT
        elif supports_count > 0 and contradicts_count == 0:
            if neutral_count > 0:
                summary = GuardedSemanticSummary.SUPPORTS_WITH_NEUTRAL
            else:
                summary = GuardedSemanticSummary.ALL_SUPPORTS
        elif contradicts_count > 0 and supports_count == 0:
            if neutral_count > 0:
                summary = GuardedSemanticSummary.CONTRADICTS_WITH_NEUTRAL
            else:
                summary = GuardedSemanticSummary.ALL_CONTRADICTS
        else:
            summary = GuardedSemanticSummary.ONLY_NEUTRAL

        return GuardedClaimVerificationResult(
            claim_id=claim_id,
            claim_text=claim_text,
            total_evidence_count=len(evidence_items),
            accepted_evidence_count=accepted_count,
            rejected_evidence_count=rejected_count,
            supports_count=supports_count,
            contradicts_count=contradicts_count,
            neutral_count=neutral_count,
            guarded_semantic_summary=summary,
            evidence_evaluations=evaluations
        )
