# Stage 40 — Quota-Safe Evaluation Runner

## Overview

The Stage 40 Quota-Safe Evaluation Runner introduces deterministic request budgeting and transparent provider accounting to allow the final 64-case / 136-claim real-world benchmark to run safely and reliably under external API constraints.

---

## 1. Why the Quota-Safe Budget Exists

NewsAPI Developer tier imposes a hard limit of **100 requests per 24-hour window**.
During real-world evaluation:
- The 64 benchmark cases contain a total of **136 claims**.
- Querying NewsAPI for every claim would require 136 HTTP requests, exceeding the 100-request daily allowance and triggering HTTP 429 rate limit exceptions mid-run.
- Without a quota-safe runner, unmanaged exhaustion causes unhandled HTTP 429 errors and premature termination of the benchmark.

---

## 2. Why the Budget Value is Exactly 99

- Stage 40 performs exactly **1 isolated NewsAPI preflight request** prior to starting the benchmark to confirm API key validity, network connectivity, and quota availability.
- Total Developer Allowance: **100 requests/day**.
- Allocated to Preflight: **1 request**.
- Available Benchmark Budget: **`NEWSAPI_BENCHMARK_MAX_REQUESTS = 99`**.

The budget constant is explicitly defined once at the top of [`backend/evaluation/run_real_world_evaluation.py`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/evaluation/run_real_world_evaluation.py).

---

## 3. Preflight vs Benchmark Accounting

The runner separates request tracking into distinct counters via `NewsAPIBudgetTracker`:

| Metric | Description |
| :--- | :--- |
| `newsapi_preflight_requests` | Count of isolated preflight verification calls (1). |
| `newsapi_benchmark_requests_made` | Actual NewsAPI HTTP requests dispatched during the 64-case benchmark ($\le 99$). |
| `newsapi_total_requests` | `preflight_requests` + `benchmark_requests_made` ($\le 100$). |
| `newsapi_claims_evaluated` | Number of extracted claims evaluated with live NewsAPI retrieval. |
| `newsapi_claims_skipped_budget` | Number of claims that bypassed NewsAPI due to quota budget exhaustion. |
| `newsapi_budget_exhausted` | Boolean flag indicating whether the 99-request limit was reached. |
| `newsapi_provider_errors` | List of any provider errors or HTTP 429 responses encountered. |

---

## 4. Behavior After Budget Exhaustion

When the 99-request benchmark budget is exhausted:
1. **Zero Outbound NewsAPI Calls:** `QuotaSafeNewsAPIRetriever` intercepts further calls and does not issue HTTP requests.
2. **Transparent Status Reporting:** NewsAPI status for affected claims is marked as `"rate_limited"` (`service_status["live_news_api"] = "rate_limited"`).
3. **Seamless Multi-Provider Continuation:** Google Fact Check API and Wikipedia General Reference continue querying normally for all remaining claims.
4. **No Claim Omission or Bias:** All 64 cases and all 136 claims are evaluated and preserved in the benchmark. Missing NewsAPI evidence is treated as unavailable retrieval, never as evidence of truth or falsity.
5. **Deterministic Ordering:** Benchmark cases and claims execute in fixed sequence, ensuring identical, reproducible budget exhaustion boundaries.

---

## 5. Verification & Tests

The implementation is verified by the unit test suite in [`backend/evaluation/test_quota_safe_runner.py`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/evaluation/test_quota_safe_runner.py):

- `test_budget_constant_and_tracker_accounting`: Confirms constant value 99 and preflight/benchmark separation.
- `test_request_budget_enforcement_at_99_limit`: Confirms exactly 99 requests are permitted and the 100th is rejected.
- `test_no_newsapi_calls_after_budget_exhaustion`: Confirms underlying retriever is never called once budget is exhausted.
- `test_remaining_claims_still_execute_with_other_providers`: Confirms pipeline completes verification with Fact Check + Wikipedia evidence when NewsAPI is exhausted.
- `test_quota_exhaustion_recorded_explicitly_in_accounting`: Confirms transparent accounting metrics.
- `test_no_duplicate_newsapi_requests_per_claim`: Confirms strictly 1 call per claim within budget and 0 after exhaustion.
- `test_deterministic_result_ordering`: Confirms reproducible execution order.
- `test_run_real_world_evaluation_mock_accounting`: Confirms end-to-end accounting in runner output payload.

All 111 backend unit tests and frontend lint/build checks pass cleanly.
