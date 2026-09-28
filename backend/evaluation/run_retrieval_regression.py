#!/usr/bin/env python3
"""
Stage 33C — Targeted Retrieval Regression Evaluation Runner
Real-Time News Verification System

Runs only the 27 cases from error_analysis.json where primary_root_cause is RETRIEVAL
against the live V2 verification pipeline (Google Fact Check + NewsAPI) and compares
results against preserved Stage 32 baseline.
"""

import json
import os
import sys
import time
import math
import statistics
import urllib.request
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi.testclient import TestClient

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.main import app
from backend.app.v2.newsapi_retriever import load_env_key
from backend.app.v2.fact_check_retriever import get_fact_check_retriever
from backend.app.v2.newsapi_retriever import get_newsapi_retriever


def sanitize_secret(obj: Any) -> Any:
    if isinstance(obj, str):
        if "key=" in obj.lower() or "secret" in obj.lower():
            import re
            return re.sub(r'key=[^&]+', 'key=[REDACTED_KEY]', obj)
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_secret(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_secret(x) for x in obj]
    return obj


def calculate_p95(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(math.ceil(0.95 * len(sorted_vals))) - 1
    idx = max(0, min(idx, len(sorted_vals) - 1))
    return sorted_vals[idx]


def run_preflight() -> bool:
    """Preflight check: 1 real NewsAPI call."""
    api_key = load_env_key("NEWS_API_KEY")
    if not api_key:
        print("PREFLIGHT ERROR: NEWS_API_KEY is not configured.")
        return False

    url = "https://newsapi.org/v2/everything?q=technology&pageSize=1"
    req = urllib.request.Request(
        url,
        headers={"X-Api-Key": api_key, "User-Agent": "RealTimeNewsVerificationSystem/2.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            if resp.getcode() == 200:
                print("PREFLIGHT: NewsAPI HTTP 200 OK — Quota available.")
                return True
            else:
                print(f"PREFLIGHT FAILED: NewsAPI returned HTTP {resp.getcode()}")
                return False
    except Exception as err:
        print(f"PREFLIGHT FAILED: {err}")
        return False


def main():
    print("=" * 80)
    print("STAGE 33C — TARGETED RETRIEVAL REGRESSION EVALUATION")
    print("=" * 80)

    # 1. Quota Preflight & Env Setup
    fc_key = os.environ.get("GOOGLE_FACT_CHECK_API_KEY", "").strip() or load_env_key("GOOGLE_FACT_CHECK_API_KEY")
    if fc_key and not os.environ.get("GOOGLE_FACT_CHECK_API_KEY"):
        os.environ["GOOGLE_FACT_CHECK_API_KEY"] = fc_key

    news_key = os.environ.get("NEWS_API_KEY", "").strip() or load_env_key("NEWS_API_KEY")
    if news_key and not os.environ.get("NEWS_API_KEY"):
        os.environ["NEWS_API_KEY"] = news_key

    if not run_preflight():
        print("ABORTING: Preflight failed. No evaluation executed.")
        sys.exit(1)

    # 2. Identify Target Cases
    ea_path = os.path.join(ROOT_DIR, "backend/evaluation/error_analysis.json")
    with open(ea_path, "r", encoding="utf-8") as f:
        ea_data = json.load(f)

    target_case_ids = [
        c["case_id"] for c in ea_data.get("case_analyses", [])
        if c.get("primary_root_cause") == "RETRIEVAL"
    ]
    print(f"\nTargeted RETRIEVAL cases identified: {len(target_case_ids)}")
    print(f"Target IDs: {target_case_ids}")

    # 3. Load Dataset
    ds_path = os.path.join(ROOT_DIR, "backend/evaluation/real_world_dataset.json")
    with open(ds_path, "r", encoding="utf-8") as f:
        full_dataset = json.load(f)

    dataset_map = {c["id"]: c for c in full_dataset}
    target_cases = [dataset_map[cid] for cid in target_case_ids if cid in dataset_map]

    print(f"Loaded {len(target_cases)} target cases from benchmark dataset.")

    # 4. Initialize TestClient
    client = TestClient(app)

    case_results = []
    response_times = []
    total_google_requests = 0
    total_newsapi_requests = 1  # 1 from preflight

    print("\nExecuting live verification on target cases with active Google Fact Check & NewsAPI...")

    for idx, case in enumerate(target_cases, 1):
        cid = case["id"]
        payload = {
            "title": case.get("title", ""),
            "text": case.get("text", ""),
            "domain": case.get("domain", "")
        }

        start_time = time.time()
        resp = client.post("/v2/verify", json=payload)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response_times.append(duration_ms)

        if resp.status_code != 200:
            print(f"  [{idx}/{len(target_cases)}] Case {cid} FAILED with HTTP {resp.status_code}: {resp.text}")
            case_results.append({
                "case_id": cid,
                "status": "error",
                "error": resp.text,
                "ground_truth": case.get("ground_truth"),
                "response_time_ms": duration_ms
            })
            continue

        data = resp.json()
        claims = data.get("claims", [])
        service_status = data.get("service_status", {})
        overall_assessment = data.get("overall_assessment", "UNVERIFIED")

        # Count evidence items
        fc_items = []
        news_items = []
        for claim in claims:
            for ev in claim.get("evidence", []):
                st = ev.get("source_type")
                if st == "FACT_CHECK_API":
                    fc_items.append(ev)
                elif st == "LIVE_NEWS_SEARCH":
                    news_items.append(ev)

        total_evidence_count = len(fc_items) + len(news_items)
        relevant_count = sum(1 for claim in claims for ev in claim.get("evidence", []) if ev.get("relevance_score", 0) > 0 or ev.get("stance") != "NEUTRAL")
        supporting_count = sum(1 for claim in claims for ev in claim.get("evidence", []) if ev.get("stance") == "SUPPORTS")
        contradicting_count = sum(1 for claim in claims for ev in claim.get("evidence", []) if ev.get("stance") == "CONTRADICTS")
        neutral_count = sum(1 for claim in claims for ev in claim.get("evidence", []) if ev.get("stance") == "NEUTRAL")

        # Track provider request counts
        total_newsapi_requests += len(claims)
        total_google_requests += len(claims)  # Minimum 1 per claim

        is_correct = (overall_assessment == case.get("ground_truth"))

        entry = {
            "case_id": cid,
            "category": case.get("category", ""),
            "title": case.get("title", ""),
            "ground_truth": case.get("ground_truth"),
            "claim_count": len(claims),
            "fact_check_count": len(fc_items),
            "live_news_count": len(news_items),
            "service_status": service_status,
            "total_evidence_count": total_evidence_count,
            "relevant_evidence_count": relevant_count,
            "supporting_evidence_count": supporting_count,
            "contradicting_evidence_count": contradicting_count,
            "neutral_evidence_count": neutral_count,
            "v2_overall_assessment": overall_assessment,
            "v2_assessment_summary": data.get("assessment_summary", ""),
            "uncertainty_level": data.get("uncertainty_level", "HIGH"),
            "evidence_strength": data.get("evidence_strength", "NONE"),
            "has_conflict": data.get("has_conflict", False),
            "response_time_ms": duration_ms,
            "retrieved_evidence": [
                {
                    "source_type": ev.get("source_type"),
                    "publisher": ev.get("publisher"),
                    "title": ev.get("title"),
                    "snippet": ev.get("snippet"),
                    "stance": ev.get("stance"),
                    "claim_reviewed": ev.get("claim_reviewed"),
                    "raw_rating": ev.get("raw_rating")
                }
                for claim in claims for ev in claim.get("evidence", [])
            ],
            "is_correct": is_correct,
            "notes": case.get("notes", "")
        }
        case_results.append(entry)

        print(f"  [{idx:02d}/{len(target_cases)}] Case {cid:8s} | GT: {case.get('ground_truth'):12s} | Pred: {overall_assessment:12s} | FC: {len(fc_items)} | News: {len(news_items)} | Latency: {duration_ms:.0f}ms")
        time.sleep(0.5)

    # 5. Output Results Payload
    output_path = os.path.join(ROOT_DIR, "backend/evaluation/real_world_results_retrieval_regression.json")
    output_payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "evaluation_type": "TARGETED_RETRIEVAL_REGRESSION_STAGE_33C",
        "target_case_count": len(case_results),
        "total_claims": sum(c.get("claim_count", 0) for c in case_results),
        "actual_google_requests_approx": total_google_requests,
        "actual_newsapi_requests": total_newsapi_requests,
        "avg_latency_ms": round(statistics.mean(response_times), 2) if response_times else 0.0,
        "median_latency_ms": round(statistics.median(response_times), 2) if response_times else 0.0,
        "p95_latency_ms": round(calculate_p95(response_times), 2) if response_times else 0.0,
        "case_results": sanitize_secret(case_results)
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print(f"\nSaved targeted results to: {output_path}")

    # 6. Load Preserved Stage 32 Combined Results for Comparative Analysis
    combined_path = os.path.join(ROOT_DIR, "backend/evaluation/real_world_results_combined.json")
    with open(combined_path, "r", encoding="utf-8") as f:
        combined_data = json.load(f)

    baseline_map = {c.get("id", c.get("case_id")): c for c in combined_data.get("case_results", [])}

    print("\n" + "=" * 80)
    print("STAGE 33C — CASE-BY-CASE RETRIEVAL REGRESSION COMPARISON")
    print("=" * 80)
    print(f"{'Case ID':8s} | {'GT':12s} | {'Old Pred':11s} -> {'New Pred':11s} | {'Old Ev':6s} -> {'New Ev':6s} | {'Old FC/News':11s} -> {'New FC/News':11s} | Status")
    print("-" * 80)

    increased_evidence_cases = []
    newly_relevant_cases = []
    verdict_changed_cases = []
    newly_correct_cases = []
    newly_incorrect_cases = []
    remaining_miss_cases = []

    for c in case_results:
        cid = c["case_id"]
        gt = c["ground_truth"]
        new_pred = c["v2_overall_assessment"]
        new_ev = c["total_evidence_count"]
        new_fc = c["fact_check_count"]
        new_news = c["live_news_count"]

        base = baseline_map.get(cid, {})
        old_pred = base.get("v2_overall_assessment", "N/A")
        old_ev = base.get("total_evidence_count", 0)
        old_fc = base.get("fact_check_count", 0)
        old_news = base.get("live_news_count", 0)

        ev_diff = new_ev - old_ev
        if ev_diff > 0:
            increased_evidence_cases.append(cid)
        if new_ev > 0 and old_ev == 0:
            newly_relevant_cases.append(cid)
        if new_pred != old_pred:
            verdict_changed_cases.append(cid)
            if new_pred == gt:
                newly_correct_cases.append(cid)
            elif old_pred == gt and new_pred != gt:
                newly_incorrect_cases.append(cid)

        if new_ev == 0:
            remaining_miss_cases.append(cid)

        status_str = "UNCHANGED"
        if new_pred == gt and old_pred != gt:
            status_str = "FIXED (CORRECT)"
        elif ev_diff > 0:
            status_str = f"+{ev_diff} EVIDENCE"
        elif new_ev == 0 and old_ev == 0:
            status_str = "STILL ZERO EV"

        print(f"{cid:8s} | {gt:12s} | {old_pred:11s} -> {new_pred:11s} | {old_ev:6d} -> {new_ev:6d} | {old_fc:2d}/{old_news:2d}        -> {new_fc:2d}/{new_news:2d}        | {status_str}")

    print("\n" + "=" * 80)
    print("STAGE 33C — TARGETED REGRESSION METRICS SUMMARY")
    print("=" * 80)
    print(f"Target Cases Evaluated:               {len(case_results)}")
    print(f"Total Claims Tested:                  {sum(c.get('claim_count', 0) for c in case_results)}")
    print(f"Total Actual NewsAPI Requests:        {total_newsapi_requests} (including 1 preflight)")
    print(f"Cases with Increased Evidence:        {len(increased_evidence_cases)} ({', '.join(increased_evidence_cases) if increased_evidence_cases else 'none'})")
    print(f"Cases with Newly Retrieved Evidence:  {len(newly_relevant_cases)} ({', '.join(newly_relevant_cases) if newly_relevant_cases else 'none'})")
    print(f"Verdict Changes:                      {len(verdict_changed_cases)} ({', '.join(verdict_changed_cases) if verdict_changed_cases else 'none'})")
    print(f"Newly Correct Verdicts:               {len(newly_correct_cases)} ({', '.join(newly_correct_cases) if newly_correct_cases else 'none'})")
    print(f"Newly Incorrect Verdicts:             {len(newly_incorrect_cases)} ({', '.join(newly_incorrect_cases) if newly_incorrect_cases else 'none'})")
    print(f"Remaining Retrieval Misses (0 ev):    {len(remaining_miss_cases)} ({', '.join(remaining_miss_cases)})")
    print(f"Average Latency:                      {output_payload['avg_latency_ms']} ms")
    print(f"Median Latency:                       {output_payload['median_latency_ms']} ms")
    print(f"P95 Latency:                          {output_payload['p95_latency_ms']} ms")
    print("=" * 80)


if __name__ == "__main__":
    main()
