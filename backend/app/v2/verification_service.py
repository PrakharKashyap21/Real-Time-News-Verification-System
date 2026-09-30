import time
import logging
import concurrent.futures
from typing import List, Optional, Dict, Any, Tuple
from backend.app.v2.schemas import (
    VerificationRequest,
    VerificationResponse,
    ClaimVerificationDetail,
    OverallAssessment,
    ClaimVerdict,
    ExtractedClaim,
    EvidenceItem
)
from backend.app.v2.claim_extractor import get_claim_extractor, ClaimExtractor
from backend.app.v2.fact_check_retriever import (
    get_fact_check_retriever,
    FactCheckAPIKeyError,
    FactCheckAPIError,
    GoogleFactCheckRetriever
)
from backend.app.v2.newsapi_retriever import (
    get_newsapi_retriever,
    NewsAPIRetriever,
    NewsAPIKeyError,
    NewsAPIError,
    NewsAPIRateLimitError
)
from backend.app.v2.news_retriever import (
    NewsRetrieverAPIError,
    NewsRetrieverRateLimitError,
    GDELTNewsRetriever
)
from backend.app.v2.reference_retriever import (
    get_reference_retriever,
    WikipediaReferenceRetriever,
    ReferenceRetrieverError,
    ReferenceRetrieverAPIError,
    ReferenceRetrieverRateLimitError,
    ReferenceRetrieverTimeoutError,
    ReferenceRetrieverMalformedResponseError
)
from backend.app.v2.evidence_aggregator import get_evidence_aggregator, EvidenceAggregator
from backend.app.v2.evidence_matcher import get_evidence_matcher, EvidenceMatcher
from backend.app.v2.stance_analyzer import get_stance_analyzer, EvidenceStanceAnalyzer
from backend.app.v2.semantic_verifier import get_semantic_verifier, SemanticVerifier
from backend.app.v2.verdict_engine import get_verdict_engine, VerdictEngine
from backend.app.v2.svm_signal import get_svm_signal_provider, SVMSignalProvider, SVMPipelineIntegrator

logger = logging.getLogger(__name__)


class VerificationService:
    """Orchestrates V2 verification workflow combining claim extraction, fact-check retrieval,

    live news retrieval (NewsAPI), general reference retrieval (Wikipedia), evidence relevance matching,
    semantic verification (NLI), evidence aggregation, verdict evaluation, and SVM signals.
    """

    def __init__(
        self,
        claim_extractor: Optional[ClaimExtractor] = None,
        fc_retriever: Optional[GoogleFactCheckRetriever] = None,
        news_retriever: Optional[Any] = None,
        reference_retriever: Optional[WikipediaReferenceRetriever] = None,
        evidence_matcher: Optional[EvidenceMatcher] = None,
        semantic_verifier: Optional[SemanticVerifier] = None,
        stance_analyzer: Optional[EvidenceStanceAnalyzer] = None,
        aggregator: Optional[EvidenceAggregator] = None,
        verdict_engine: Optional[VerdictEngine] = None,
        svm_provider: Optional[SVMSignalProvider] = None,
        mock_mode: bool = False
    ):
        self.claim_extractor = claim_extractor or get_claim_extractor()
        self.fc_retriever = fc_retriever or get_fact_check_retriever(mock_mode=mock_mode)
        self.news_retriever = news_retriever or get_newsapi_retriever(mock_mode=mock_mode)
        self.reference_retriever = reference_retriever or get_reference_retriever(mock_mode=mock_mode)
        self.evidence_matcher = evidence_matcher or get_evidence_matcher()
        self.semantic_verifier = semantic_verifier or get_semantic_verifier(mock_mode=mock_mode)
        self.stance_analyzer = stance_analyzer or get_stance_analyzer()
        self.aggregator = aggregator or get_evidence_aggregator()
        self.verdict_engine = verdict_engine or get_verdict_engine()
        self.svm_provider = svm_provider or get_svm_signal_provider()
        self.integrator = SVMPipelineIntegrator(self.svm_provider)

    def _fetch_fc_evidence(self, claim: ExtractedClaim) -> Tuple[List[EvidenceItem], str]:
        """Safely queries Google Fact Check API for a claim with error status mapping."""
        try:
            evidence = self.fc_retriever.search_claim(claim)
            return evidence, "ok"
        except FactCheckAPIKeyError:
            return [], "missing_api_key"
        except FactCheckAPIError as fc_err:
            return [], f"error_{fc_err.status_code}"
        except Exception:
            return [], "error"

    def _fetch_news_evidence(self, claim: ExtractedClaim) -> Tuple[List[EvidenceItem], str]:
        """Safely queries Live News API for a claim with error status mapping."""
        try:
            evidence = self.news_retriever.search_claim_news(claim)
            return evidence, "ok"
        except (NewsAPIKeyError, FactCheckAPIKeyError):
            return [], "missing_api_key"
        except (NewsAPIRateLimitError, NewsRetrieverRateLimitError):
            return [], "rate_limited"
        except (NewsAPIError, NewsRetrieverAPIError) as news_err:
            if news_err.status_code == 429:
                return [], "rate_limited"
            elif news_err.status_code == 401:
                return [], "error_401"
            elif news_err.status_code == 504:
                return [], "error_504"
            else:
                return [], f"error_{news_err.status_code}"
        except Exception:
            return [], "error"

    def _fetch_ref_evidence(self, claim: ExtractedClaim) -> Tuple[List[EvidenceItem], str]:
        """Safely queries Wikipedia Reference API for a claim with error status mapping."""
        try:
            evidence = self.reference_retriever.search_claim_reference(claim)
            return evidence, "ok"
        except ReferenceRetrieverRateLimitError:
            return [], "rate_limited"
        except ReferenceRetrieverTimeoutError:
            return [], "timeout"
        except ReferenceRetrieverAPIError as ref_err:
            return [], f"error_{ref_err.status_code}"
        except ReferenceRetrieverMalformedResponseError:
            return [], "malformed_response"
        except Exception:
            return [], "error"

    def verify_news(self, request: VerificationRequest) -> VerificationResponse:
        t_pipeline_start = time.perf_counter()
        title = (request.title or "").strip()
        text = (request.text or "").strip()
        max_claims = request.max_claims or 5

        # 1. Claim extraction
        t_ext_start = time.perf_counter()
        extracted_claims = self.claim_extractor.extract_claims(title=title, text=text, max_claims=max_claims)
        t_ext_ms = (time.perf_counter() - t_ext_start) * 1000

        # 2. Article-level V1 SVM Linguistic Signal
        article_svm_signal = None
        if request.include_linguistic_signal:
            try:
                article_svm_signal = self.svm_provider.get_signal(title=title, text=text)
            except Exception:
                pass

        service_status: Dict[str, str] = {
            "fact_check_api": "ok",
            "live_news_api": "ok",
            "reference_api": "ok"
        }

        # 3. Concurrent Bounded Evidence Retrieval across all claims and independent providers
        t_ret_start = time.perf_counter()
        claim_evidence_map: Dict[int, Dict[str, List[EvidenceItem]]] = {
            i: {"fc": [], "news": [], "ref": []} for i in range(len(extracted_claims))
        }

        if extracted_claims:
            max_workers = min(12, max(1, len(extracted_claims) * 3))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for idx, claim in enumerate(extracted_claims):
                    f_fc = executor.submit(self._fetch_fc_evidence, claim)
                    f_news = executor.submit(self._fetch_news_evidence, claim)
                    f_ref = executor.submit(self._fetch_ref_evidence, claim)
                    futures[f_fc] = (idx, "fact_check_api")
                    futures[f_news] = (idx, "live_news_api")
                    futures[f_ref] = (idx, "reference_api")

                # Bounded timeout for all external retrievals (12.0s max)
                done, not_done = concurrent.futures.wait(futures.keys(), timeout=12.0)

                for f in done:
                    idx, provider_key = futures[f]
                    try:
                        ev_list, status_val = f.result()
                        if provider_key == "fact_check_api":
                            claim_evidence_map[idx]["fc"] = ev_list
                            if status_val != "ok" or service_status["fact_check_api"] == "ok":
                                service_status["fact_check_api"] = status_val
                        elif provider_key == "live_news_api":
                            claim_evidence_map[idx]["news"] = ev_list
                            if status_val != "ok" or service_status["live_news_api"] == "ok":
                                service_status["live_news_api"] = status_val
                        elif provider_key == "reference_api":
                            claim_evidence_map[idx]["ref"] = ev_list
                            if status_val != "ok" or service_status["reference_api"] == "ok":
                                service_status["reference_api"] = status_val
                    except Exception:
                        service_status[provider_key] = "error"

                for f in not_done:
                    _, provider_key = futures[f]
                    service_status[provider_key] = "timeout"

        t_ret_ms = (time.perf_counter() - t_ret_start) * 1000

        # 4. Evidence Matching, Semantic NLI Verification, Aggregation, and Verdict Construction
        claim_details: List[ClaimVerificationDetail] = []
        t_match_ms = 0.0
        t_nli_ms = 0.0
        t_agg_ms = 0.0
        total_evidence_evaluated = 0

        for idx, claim in enumerate(extracted_claims):
            # Preserve exact deterministic ordering: Fact Check -> Live News -> General Reference
            fc_evidence = claim_evidence_map[idx]["fc"]
            news_evidence = claim_evidence_map[idx]["news"]
            ref_evidence = claim_evidence_map[idx]["ref"]
            combined_evidence = fc_evidence + news_evidence + ref_evidence

            # Evidence relevance matching (deterministic gate)
            t_m0 = time.perf_counter()
            matched_evidence = self.evidence_matcher.process_claim_evidence(claim, combined_evidence)
            t_match_ms += (time.perf_counter() - t_m0) * 1000

            # Evidence semantic verification (single NLI model with pair-level deduplication)
            t_n0 = time.perf_counter()
            semantically_verified_evidence = self.semantic_verifier.process_claim_evidence(claim, matched_evidence)
            t_nli_ms += (time.perf_counter() - t_n0) * 1000
            total_evidence_evaluated += len(matched_evidence)

            # Evidence aggregation
            t_a0 = time.perf_counter()
            summary = self.aggregator.aggregate_evidence(claim, semantically_verified_evidence)

            # Claim verdict evaluation
            base_result = self.verdict_engine.verify_summary(summary)

            # Attach claim-level SVM signal without mutating verdict
            res_with_svm = self.integrator.attach_signal_to_result(claim, base_result)
            t_agg_ms += (time.perf_counter() - t_a0) * 1000

            claim_details.append(
                ClaimVerificationDetail(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    verdict=res_with_svm.verdict,
                    reasoning=res_with_svm.reasoning,
                    evidence_strength=res_with_svm.evidence_strength,
                    uncertainty_level=res_with_svm.uncertainty_level,
                    has_conflicting_evidence=res_with_svm.has_conflicting_evidence,
                    supporting_evidence_count=res_with_svm.supporting_evidence_count,
                    contradicting_evidence_count=res_with_svm.contradicting_evidence_count,
                    neutral_evidence_count=res_with_svm.neutral_evidence_count,
                    keywords=claim.keywords,
                    evidence_summary=summary,
                    evidence=summary.all_evidence,
                    linguistic_signal=res_with_svm.linguistic_signal,
                    semantic_relation=res_with_svm.semantic_relation,
                    semantic_model=res_with_svm.semantic_model,
                    semantic_evidence_count=res_with_svm.semantic_evidence_count
                )
            )

        # 5. Synthesize overall assessment deterministically and conservatively
        has_supported = any(c.verdict == ClaimVerdict.SUPPORTED for c in claim_details)
        has_contradicted = any(c.verdict == ClaimVerdict.CONTRADICTED for c in claim_details)
        has_conflict = any(c.has_conflicting_evidence for c in claim_details) or (has_supported and has_contradicted)

        if not claim_details:
            overall = OverallAssessment.UNVERIFIED
            summary_msg = "No factual claims were extracted from the input text."
        elif has_supported and has_contradicted:
            overall = OverallAssessment.UNVERIFIED
            summary_msg = "Mixed claim results: article contains both supported and contradicted claims."
        elif has_supported and all(c.verdict == ClaimVerdict.SUPPORTED for c in claim_details):
            overall = OverallAssessment.SUPPORTED
            summary_msg = "All claims in this article were confirmed by factual evidence."
        elif has_contradicted and all(c.verdict in (ClaimVerdict.CONTRADICTED, ClaimVerdict.UNVERIFIED) for c in claim_details):
            if all(c.verdict == ClaimVerdict.CONTRADICTED for c in claim_details):
                overall = OverallAssessment.CONTRADICTED
                summary_msg = "All claims in this article were contradicted by factual evidence."
            else:
                overall = OverallAssessment.CONTRADICTED
                summary_msg = "One or more claims in this article were contradicted by factual evidence, with no supported claims."
        elif has_supported and not has_contradicted:
            overall = OverallAssessment.UNVERIFIED
            summary_msg = "Some claims in this article were supported, but others remain unverified."
        else:
            overall = OverallAssessment.UNVERIFIED
            summary_msg = "Insufficient conclusive evidence found to verify the claims in this article."

        t_total_ms = (time.perf_counter() - t_pipeline_start) * 1000

        logger.debug(
            "V2 Timing breakdown: extraction=%.2fms, retrieval=%.2fms, matching=%.2fms, nli=%.2fms, aggregation=%.2fms, total=%.2fms (claims=%d, evidence_items=%d)",
            t_ext_ms, t_ret_ms, t_match_ms, t_nli_ms, t_agg_ms, t_total_ms, len(extracted_claims), total_evidence_evaluated
        )

        return VerificationResponse(
            overall_assessment=overall,
            assessment_summary=summary_msg,
            has_conflict=has_conflict,
            claims=claim_details,
            linguistic_signal=article_svm_signal,
            service_status=service_status
        )


_verification_service_instance = None


def get_verification_service(mock_mode: bool = False) -> VerificationService:
    global _verification_service_instance
    if mock_mode:
        return VerificationService(mock_mode=True)
    if _verification_service_instance is None:
        _verification_service_instance = VerificationService(mock_mode=False)
    return _verification_service_instance
