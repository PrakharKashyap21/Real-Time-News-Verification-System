import os
import json
import pytest
from backend.evaluation.aggregate_evaluation_batches import (
    aggregate_batches,
    compute_aggregate_metrics,
    IncompleteBatchEvaluationError
)

def test_missing_batch_raises_error(tmp_path):
    b1 = tmp_path / "b1.json"
    b1.write_text(json.dumps({"case_results": [{"id": f"c_{i}"} for i in range(45)]}))
    non_existent_b2 = tmp_path / "b2.json"

    with pytest.raises(IncompleteBatchEvaluationError) as exc:
        aggregate_batches(str(b1), str(non_existent_b2))
    assert "Batch 2 file not found" in str(exc.value)


def test_incomplete_batch_count_raises_error(tmp_path):
    b1 = tmp_path / "b1.json"
    b1.write_text(json.dumps({"case_results": [{"id": f"c_{i}"} for i in range(40)]})) # 40 instead of 45
    b2 = tmp_path / "b2.json"
    b2.write_text(json.dumps({"case_results": [{"id": f"c_{i}"} for i in range(40, 59)]})) # 19 cases

    with pytest.raises(IncompleteBatchEvaluationError) as exc:
        aggregate_batches(str(b1), str(b2))
    assert "Batch 1 must contain exactly 45 cases" in str(exc.value)


def test_duplicate_case_ids_raises_error(tmp_path):
    b1 = tmp_path / "b1.json"
    b1.write_text(json.dumps({"case_results": [{"id": f"c_{i}"} for i in range(45)]}))
    b2 = tmp_path / "b2.json"
    # Overlap with b1
    b2.write_text(json.dumps({"case_results": [{"id": f"c_{i}"} for i in range(44, 63)]}))

    with pytest.raises(IncompleteBatchEvaluationError) as exc:
        aggregate_batches(str(b1), str(b2))
    assert "unique IDs" in str(exc.value)


def test_valid_64_case_aggregation(tmp_path):
    dataset_cases = [{"id": f"c_{i}"} for i in range(64)]
    dataset_file = tmp_path / "dataset.json"
    dataset_file.write_text(json.dumps(dataset_cases))

    b1_cases = [
        {
            "id": f"c_{i}",
            "ground_truth": "SUPPORTED" if i < 16 else ("CONTRADICTED" if i < 39 else "UNVERIFIED"),
            "v2_overall_assessment": "SUPPORTED" if i < 10 else "UNVERIFIED",
            "is_correct": i < 10,
            "claim_count": 2,
            "fact_check_count": 1 if i < 10 else 0,
            "live_news_count": 1 if i < 10 else 0,
            "total_evidence_count": 2 if i < 10 else 0,
            "relevant_evidence_count": 2 if i < 10 else 0,
            "supporting_evidence_count": 2 if i < 10 else 0,
            "contradicting_evidence_count": 0,
            "neutral_evidence_count": 0,
            "has_conflict": False,
            "response_time_ms": 100.0,
            "service_status": {"fact_check_api": "ok", "live_news_api": "ok"}
        }
        for i in range(45)
    ]
    b2_cases = [
        {
            "id": f"c_{i}",
            "ground_truth": "UNVERIFIED",
            "v2_overall_assessment": "UNVERIFIED",
            "is_correct": True,
            "claim_count": 2,
            "fact_check_count": 0,
            "live_news_count": 0,
            "total_evidence_count": 0,
            "relevant_evidence_count": 0,
            "supporting_evidence_count": 0,
            "contradicting_evidence_count": 0,
            "neutral_evidence_count": 0,
            "has_conflict": False,
            "response_time_ms": 150.0,
            "service_status": {"fact_check_api": "ok", "live_news_api": "ok"}
        }
        for i in range(45, 64)
    ]

    b1_file = tmp_path / "b1.json"
    b1_file.write_text(json.dumps({"timestamp": "2026-09-27T10:00:00Z", "case_results": b1_cases}))
    b2_file = tmp_path / "b2.json"
    b2_file.write_text(json.dumps({"timestamp": "2026-09-27T12:00:00Z", "case_results": b2_cases}))

    out_file = tmp_path / "aggregated.json"
    res = aggregate_batches(str(b1_file), str(b2_file), str(dataset_file), str(out_file))

    assert len(res["case_results"]) == 64
    assert res["metrics"]["total_cases"] == 64
    assert res["metrics"]["claim_extraction_success_rate"] == 100.0
    assert os.path.exists(out_file)
