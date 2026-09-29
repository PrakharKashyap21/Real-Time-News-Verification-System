from typing import List, Optional, Tuple
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    ClaimEvidenceSummary,
    ClaimVerdict,
    ClaimVerificationResult,
    EvidenceStrength,
    UncertaintyLevel,
    StanceType
)
from backend.app.v2.evidence_aggregator import get_evidence_aggregator, EvidenceAggregator


def evaluate_uncertainty(summary: ClaimEvidenceSummary) -> Tuple[EvidenceStrength, UncertaintyLevel]:
    """Evaluates evidence strength and uncertainty level based strictly on the aggregated evidence summary."""
    if not summary or summary.total_evidence_count == 0:
        return EvidenceStrength.NONE, UncertaintyLevel.HIGH

    supp_count = summary.supporting_evidence_count
    contra_count = summary.contradicting_evidence_count
    has_conflict = summary.has_conflicting_evidence

    # If evidence items exist, but no explicit supporting or contradicting stance exists
    if supp_count == 0 and contra_count == 0:
        return EvidenceStrength.LIMITED, UncertaintyLevel.HIGH

    # If supporting and contradicting evidence conflict
    if has_conflict:
        return EvidenceStrength.LIMITED, UncertaintyLevel.HIGH

    # Count unique independent source domains with explicit supporting/contradicting stances
    explicit_domains = set()
    if summary.all_evidence:
        for item in summary.all_evidence:
            if item.stance in (StanceType.SUPPORTS, StanceType.CONTRADICTS):
                clean_dom = str(item.domain).strip().lower() if item.domain else ""
                if clean_dom and clean_dom != "unknown":
                    explicit_domains.add(clean_dom)

    unique_explicit_domains = len(explicit_domains)

    if unique_explicit_domains >= 2:
        return EvidenceStrength.STRONG, UncertaintyLevel.LOW

    return EvidenceStrength.MODERATE, UncertaintyLevel.MEDIUM


class VerdictEngine:
    """Deterministic, transparent claim verification engine with explicit evidence strength and uncertainty analysis."""

    def __init__(self, aggregator: Optional[EvidenceAggregator] = None):
        self.aggregator = aggregator or get_evidence_aggregator()

    def verify_summary(self, summary: ClaimEvidenceSummary) -> ClaimVerificationResult:
        """Determines the claim verdict, evidence strength, uncertainty level, and reasoning from summary."""
        claim_id = summary.claim_id if summary and summary.claim_id else "unknown_claim"
        supp_count = summary.supporting_evidence_count if summary else 0
        contra_count = summary.contradicting_evidence_count if summary else 0
        neut_count = summary.neutral_evidence_count if summary else 0
        sem_count = summary.semantic_evidence_count if summary else 0
        sem_model = summary.semantic_model if summary else "cross-encoder/nli-distilroberta-base"

        strength, uncertainty = evaluate_uncertainty(summary)

        # Rule 4: Both supporting and contradicting evidence exist
        if supp_count > 0 and contra_count > 0:
            return ClaimVerificationResult(
                claim_id=claim_id,
                verdict=ClaimVerdict.UNVERIFIED,
                supporting_evidence_count=supp_count,
                contradicting_evidence_count=contra_count,
                neutral_evidence_count=neut_count,
                has_conflicting_evidence=True,
                reasoning="Supporting and contradicting evidence were both found; the claim is unverified.",
                evidence_strength=strength,
                uncertainty_level=uncertainty,
                semantic_relation="CONFLICT",
                semantic_model=sem_model,
                semantic_evidence_count=sem_count
            )

        # Rule 2: Supporting evidence exists, no contradicting evidence
        if supp_count > 0 and contra_count == 0:
            return ClaimVerificationResult(
                claim_id=claim_id,
                verdict=ClaimVerdict.SUPPORTED,
                supporting_evidence_count=supp_count,
                contradicting_evidence_count=contra_count,
                neutral_evidence_count=neut_count,
                has_conflicting_evidence=False,
                reasoning="Supporting evidence was found with no contradicting evidence.",
                evidence_strength=strength,
                uncertainty_level=uncertainty,
                semantic_relation="SUPPORTS",
                semantic_model=sem_model,
                semantic_evidence_count=sem_count
            )

        # Rule 3: Contradicting evidence exists, no supporting evidence
        if contra_count > 0 and supp_count == 0:
            return ClaimVerificationResult(
                claim_id=claim_id,
                verdict=ClaimVerdict.CONTRADICTED,
                supporting_evidence_count=supp_count,
                contradicting_evidence_count=contra_count,
                neutral_evidence_count=neut_count,
                has_conflicting_evidence=False,
                reasoning="Contradicting evidence was found with no supporting evidence.",
                evidence_strength=strength,
                uncertainty_level=uncertainty,
                semantic_relation="CONTRADICTS",
                semantic_model=sem_model,
                semantic_evidence_count=sem_count
            )

        # Rule 1, 5, 6: No supporting or contradicting evidence found
        return ClaimVerificationResult(
            claim_id=claim_id,
            verdict=ClaimVerdict.UNVERIFIED,
            supporting_evidence_count=supp_count,
            contradicting_evidence_count=contra_count,
            neutral_evidence_count=neut_count,
            has_conflicting_evidence=False,
            reasoning="No supporting or contradicting evidence was found.",
            evidence_strength=strength,
            uncertainty_level=uncertainty,
            semantic_relation="NEUTRAL" if neut_count > 0 else "NO_EVIDENCE",
            semantic_model=sem_model,
            semantic_evidence_count=sem_count
        )

    def verify_claim(
        self,
        claim: ExtractedClaim,
        evidence_items: Optional[List[EvidenceItem]] = None
    ) -> ClaimVerificationResult:
        """Aggregates evidence for an ExtractedClaim and evaluates its verdict."""
        summary = self.aggregator.aggregate_evidence(claim, evidence_items)
        return self.verify_summary(summary)


_verdict_engine_instance = None


def get_verdict_engine() -> VerdictEngine:
    global _verdict_engine_instance
    if _verdict_engine_instance is None:
        _verdict_engine_instance = VerdictEngine()
    return _verdict_engine_instance
