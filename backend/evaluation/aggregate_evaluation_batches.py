import os
import json
import math
import statistics
from typing import Dict, List, Any, Optional

EXPECTED_BATCH_1_COUNT = 45
EXPECTED_BATCH_2_COUNT = 19
EXPECTED_TOTAL_COUNT = 64


class IncompleteBatchEvaluationError(ValueError):
    """Raised when one or more evaluation batch files are missing, incomplete, or corrupted."""
    pass


def calculate_p95(values: List[float]) -> float:
    """Calculates 95th percentile value from a list of numbers."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(math.ceil(0.95 * len(sorted_vals))) - 1
    idx = max(0, min(idx, len(sorted_vals) - 1))
    return sorted_vals[idx]


def compute_aggregate_metrics(case_results: List[Dict[str, Any]], eval_mode_title: str) -> Dict[str, Any]:
    """Computes standard benchmark metrics directly from raw case records."""
    total_cases = len(case_results)
    if total_cases == 0:
        raise ValueError("Cannot compute metrics from empty case list.")

    # 1. Claim extraction success
    extraction_success_count = sum(1 for c in case_results if c.get("claim_count", 0) > 0)
    extraction_success_rate = round((extraction_success_count / total_cases) * 100, 2)

    # 2. Retrieval hit rates
    fact_check_hits = sum(1 for c in case_results if c.get("fact_check_count", 0) > 0)
    fact_check_hit_rate = round((fact_check_hits / total_cases) * 100, 2)

    live_news_hits = sum(1 for c in case_results if c.get("live_news_count", 0) > 0)
    live_news_hit_rate = round((live_news_hits / total_cases) * 100, 2)

    evidence_relevant_cases = sum(1 for c in case_results if c.get("relevant_evidence_count", 0) > 0)
    evidence_relevance_rate = round((evidence_relevant_cases / total_cases) * 100, 2)

    # 3. Evidence Stance Counts
    total_supports = sum(c.get("supporting_evidence_count", 0) for c in case_results)
    total_contradicts = sum(c.get("contradicting_evidence_count", 0) for c in case_results)
    total_neutrals = sum(c.get("neutral_evidence_count", 0) for c in case_results)
    total_all_evidence = sum(c.get("total_evidence_count", 0) for c in case_results)

    retrieved_evidence_stance_count = total_supports + total_contradicts + total_neutrals
    stance_coverage_rate = round(
        (retrieved_evidence_stance_count / total_all_evidence) * 100, 2
    ) if total_all_evidence > 0 else 0.0

    verdict_coverage_count = sum(1 for c in case_results if c.get("v2_overall_assessment") in ["SUPPORTED", "CONTRADICTED", "UNVERIFIED"])
    verdict_coverage_rate = round((verdict_coverage_count / total_cases) * 100, 2)

    # 4. Accuracy
    overall_correct_count = sum(1 for c in case_results if c.get("is_correct"))
    overall_accuracy = round((overall_correct_count / total_cases) * 100, 2)

    # Clean case accuracy
    valid_cases = [c for c in case_results if all(v == "ok" for v in c.get("service_status", {}).values())]
    if valid_cases:
        valid_correct_count = sum(1 for c in valid_cases if c.get("is_correct"))
        valid_accuracy: Any = round((valid_correct_count / len(valid_cases)) * 100, 2)
    else:
        valid_accuracy = "N/A — no fully-clean cases"

    unverified_count = sum(1 for c in case_results if c.get("v2_overall_assessment") == "UNVERIFIED")
    unverified_rate = round((unverified_count / total_cases) * 100, 2)

    # 5. False Positive & False Negative Rates
    false_ground_truth_cases = [c for c in case_results if c.get("ground_truth") == "CONTRADICTED"]
    false_positives = sum(1 for c in false_ground_truth_cases if c.get("v2_overall_assessment") == "SUPPORTED")
    false_positive_rate = round((false_positives / len(false_ground_truth_cases)) * 100, 2) if false_ground_truth_cases else 0.0

    true_ground_truth_cases = [c for c in case_results if c.get("ground_truth") == "SUPPORTED"]
    false_negatives = sum(1 for c in true_ground_truth_cases if c.get("v2_overall_assessment") == "CONTRADICTED")
    false_negative_rate = round((false_negatives / len(true_ground_truth_cases)) * 100, 2) if true_ground_truth_cases else 0.0

    conflict_count = sum(1 for c in case_results if c.get("has_conflict"))
    conflict_rate = round((conflict_count / total_cases) * 100, 2)

    # 6. Service Unavailability
    live_news_unavailability_count = sum(
        1 for c in case_results
        if c.get("service_status", {}).get("live_news_api", "ok") != "ok"
    )
    live_news_unavailability_rate = round((live_news_unavailability_count / total_cases) * 100, 2)

    fc_unavailability_count = sum(
        1 for c in case_results
        if c.get("service_status", {}).get("fact_check_api", "ok") != "ok"
    )

    # 7. Classification Metrics (Precision, Recall, F1)
    def calc_p_r_f1(pred_label: str, gt_label: str):
        tp = sum(1 for c in case_results if c.get("v2_overall_assessment") == pred_label and c.get("ground_truth") == gt_label)
        fp = sum(1 for c in case_results if c.get("v2_overall_assessment") == pred_label and c.get("ground_truth") != gt_label)
        fn = sum(1 for c in case_results if c.get("v2_overall_assessment") != pred_label and c.get("ground_truth") == gt_label)

        precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        return round(precision, 2), round(recall, 2), round(f1, 2)

    p_supp, r_supp, f1_supp = calc_p_r_f1("SUPPORTED", "SUPPORTED")
    p_cont, r_cont, f1_cont = calc_p_r_f1("CONTRADICTED", "CONTRADICTED")
    p_unv, r_unv, f1_unv = calc_p_r_f1("UNVERIFIED", "UNVERIFIED")
    macro_f1 = round((f1_supp + f1_cont + f1_unv) / 3, 2)

    support_supp = sum(1 for c in case_results if c.get("ground_truth") == "SUPPORTED")
    support_cont = sum(1 for c in case_results if c.get("ground_truth") == "CONTRADICTED")
    support_unv = sum(1 for c in case_results if c.get("ground_truth") == "UNVERIFIED")
    weighted_f1 = round((f1_supp * support_supp + f1_cont * support_cont + f1_unv * support_unv) / total_cases, 2)

    pred_supp_count = sum(1 for c in case_results if c.get("v2_overall_assessment") == "SUPPORTED")
    pred_cont_count = sum(1 for c in case_results if c.get("v2_overall_assessment") == "CONTRADICTED")
    pred_unv_count = sum(1 for c in case_results if c.get("v2_overall_assessment") == "UNVERIFIED")

    fc_evidence_count = sum(
        1 for c in case_results for ev in c.get("retrieved_evidence", []) if ev.get("source_type") == "FACT_CHECK_API"
    )
    newsapi_evidence_count = sum(
        1 for c in case_results for ev in c.get("retrieved_evidence", []) if ev.get("source_type") == "LIVE_NEWS_SEARCH"
    )

    # 8. Latency
    response_times = [c.get("response_time_ms", 0.0) for c in case_results if "response_time_ms" in c]
    avg_latency = round(statistics.mean(response_times), 2) if response_times else 0.0
    median_latency = round(statistics.median(response_times), 2) if response_times else 0.0
    p95_latency = round(calculate_p95(response_times), 2) if response_times else 0.0

    # 9. Confusion Matrix
    labels = ["SUPPORTED", "CONTRADICTED", "UNVERIFIED"]
    confusion_matrix = {gt: {pred: 0 for pred in labels} for gt in labels}
    for c in case_results:
        gt = c.get("ground_truth")
        pred = c.get("v2_overall_assessment")
        if gt in confusion_matrix and pred in confusion_matrix[gt]:
            confusion_matrix[gt][pred] += 1

    # 10. Failure Breakdown
    failure_counts = {
        "claim_extraction_failure": 0,
        "fact_check_retrieval_failure": 0,
        "live_news_retrieval_failure": 0,
        "irrelevant_evidence": 0,
        "stance_error": 0,
        "verdict_logic_error": 0,
        "source_conflict": 0,
        "insufficient_evidence": 0,
        "ground_truth_ambiguity": 0,
        "service_failure": 0,
        "none": 0
    }
    for c in case_results:
        fc = c.get("failure_classification", "none")
        failure_counts[fc] = failure_counts.get(fc, 0) + 1

    fc_status = "configured" if fc_unavailability_count < total_cases else "unavailable"
    news_status = "configured" if live_news_unavailability_count < total_cases else "unavailable"

    return {
        "evaluation_mode": eval_mode_title,
        "google_fact_check_api_status": fc_status,
        "news_api_status": news_status,
        "total_cases": total_cases,
        "correct_cases_count": overall_correct_count,
        "incorrect_cases_count": total_cases - overall_correct_count,
        "claim_extraction_success_rate": extraction_success_rate,
        "fact_check_hit_rate": fact_check_hit_rate,
        "live_news_hit_rate": live_news_hit_rate,
        "evidence_relevance_rate": evidence_relevance_rate,
        "retrieved_evidence_stance_coverage": stance_coverage_rate,
        "supports_evidence_count": total_supports,
        "contradicts_evidence_count": total_contradicts,
        "neutral_evidence_count": total_neutrals,
        "total_all_evidence_count": total_all_evidence,
        "fact_check_evidence_count": fc_evidence_count,
        "newsapi_evidence_count": newsapi_evidence_count,
        "verdict_coverage_rate": verdict_coverage_rate,
        "overall_ground_truth_accuracy": overall_accuracy,
        "accuracy_fully_clean_cases": valid_accuracy,
        "fully_clean_case_count": len(valid_cases),
        "predicted_supported_count": pred_supp_count,
        "predicted_contradicted_count": pred_cont_count,
        "predicted_unverified_count": pred_unv_count,
        "predicted_supported_rate": round((pred_supp_count / total_cases) * 100, 2),
        "predicted_contradicted_rate": round((pred_cont_count / total_cases) * 100, 2),
        "predicted_unverified_rate": round((pred_unv_count / total_cases) * 100, 2),
        "unverified_rate": unverified_rate,
        "false_positive_rate": false_positive_rate,
        "false_negative_rate": false_negative_rate,
        "conflict_rate": conflict_rate,
        "conflict_count": conflict_count,
        "live_news_unavailability_rate": live_news_unavailability_rate,
        "live_news_unavailability_count": live_news_unavailability_count,
        "gdelt_unavailability_rate": live_news_unavailability_rate,
        "gdelt_unavailability_count": live_news_unavailability_count,
        "precision_supported": p_supp,
        "recall_supported": r_supp,
        "f1_supported": f1_supp,
        "support_supported": support_supp,
        "precision_contradicted": p_cont,
        "recall_contradicted": r_cont,
        "f1_contradicted": f1_cont,
        "support_contradicted": support_cont,
        "precision_unverified": p_unv,
        "recall_unverified": r_unv,
        "f1_unverified": f1_unv,
        "support_unverified": support_unv,
        "macro_f1_score": macro_f1,
        "weighted_f1_score": weighted_f1,
        "avg_latency_ms": avg_latency,
        "median_latency_ms": median_latency,
        "p95_latency_ms": p95_latency,
        "confusion_matrix": confusion_matrix,
        "failure_categories": failure_counts
    }


def aggregate_batches(
    batch_1_path: str,
    batch_2_path: str,
    dataset_path: Optional[str] = None,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Combines Batch 1 and Batch 2 evaluation results into a complete 64-case benchmark payload."""
    if not os.path.exists(batch_1_path):
        raise IncompleteBatchEvaluationError(f"Batch 1 file not found: {batch_1_path}")
    if not os.path.exists(batch_2_path):
        raise IncompleteBatchEvaluationError(f"Batch 2 file not found: {batch_2_path}")

    with open(batch_1_path, "r", encoding="utf-8") as f:
        b1_data = json.load(f)
    with open(batch_2_path, "r", encoding="utf-8") as f:
        b2_data = json.load(f)

    b1_cases = b1_data.get("case_results", [])
    b2_cases = b2_data.get("case_results", [])

    if len(b1_cases) != EXPECTED_BATCH_1_COUNT:
        raise IncompleteBatchEvaluationError(
            f"Batch 1 must contain exactly {EXPECTED_BATCH_1_COUNT} cases, found {len(b1_cases)}"
        )
    if len(b2_cases) != EXPECTED_BATCH_2_COUNT:
        raise IncompleteBatchEvaluationError(
            f"Batch 2 must contain exactly {EXPECTED_BATCH_2_COUNT} cases, found {len(b2_cases)}"
        )

    combined_cases = b1_cases + b2_cases
    combined_ids = [c["id"] for c in combined_cases]

    if len(set(combined_ids)) != EXPECTED_TOTAL_COUNT:
        raise IncompleteBatchEvaluationError(
            f"Combined batches contain {len(set(combined_ids))} unique IDs; expected {EXPECTED_TOTAL_COUNT} unique IDs"
        )

    if dataset_path and os.path.exists(dataset_path):
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        expected_ids = [c["id"] for c in dataset]
        if combined_ids != expected_ids:
            raise IncompleteBatchEvaluationError(
                "Combined case IDs and ordering do not match the expected 64-case benchmark dataset"
            )

    eval_mode = "COMPLETE REAL-WORLD API EVALUATION (AGGREGATED)"
    metrics = compute_aggregate_metrics(combined_cases, eval_mode)

    output_payload = {
        "timestamp": b2_data.get("timestamp", b1_data.get("timestamp")),
        "evaluation_mode": eval_mode,
        "batches_aggregated": [
            {"batch": 1, "case_count": len(b1_cases)},
            {"batch": 2, "case_count": len(b2_cases)}
        ],
        "metrics": metrics,
        "case_results": combined_cases
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2)

    return output_payload
