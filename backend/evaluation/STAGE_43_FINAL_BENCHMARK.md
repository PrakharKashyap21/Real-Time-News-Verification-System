# Stage 43 — Final 64-Case Benchmark Evaluation Report

## 1. Executive Summary

This report documents the final end-to-end evaluation of the Real-Time News Verification System (V2) across the authoritative 64-case / 136-claim real-world benchmark following the generalized Stage 42 Fact-Check Proposition Matching fix.

The evaluation was performed using live real-world external retrieval (Google Fact Check API, Wikipedia Reference, and quota-safe NewsAPI) with cross-encoder NLI semantic relation verification (`cross-encoder/nli-distilroberta-base`).

### Key Performance Summary
- **Overall Accuracy:** **48.44%** (31 / 64 cases correct)
- **Macro F1 Score:** **36.96**
- **Weighted F1 Score:** **41.57**
- **CONTRADICTED Recall:** **52.17%** (12 / 23 cases)
- **CONTRADICTED Precision:** **60.00%** (12 / 20 predictions)
- **CONTRADICTED F1:** **55.81**
- **UNVERIFIED Recall:** **76.00%** (19 / 25 cases)
- **UNVERIFIED Precision:** **43.18%** (19 / 44 predictions)
- **UNVERIFIED F1:** **55.07**
- **SUPPORTED Recall:** **0.00%** (0 / 16 cases)
- **FPR for SUPPORTED:** **0.00%** (0 / 48 non-supported cases)
- **FPR for CONTRADICTED:** **19.51%** (8 / 41 non-contradicted cases)
- **FNR for SUPPORTED:** **100.00%** (16 / 16 ground-truth supported cases)
- **FNR for CONTRADICTED:** **47.83%** (11 / 23 ground-truth contradicted cases)
- **Conflict Rate:** **4.69%** (3 cases)
- **Total Accepted Evidence:** **113 items**
- **Total NewsAPI Requests:** **100** (1 preflight + 99 benchmark, 0 provider errors, strictly quota-safe)
- **Average Latency:** **2,190.42 ms** (Median: 2,144.39 ms, P95: 2,751.60 ms)

---

## 2. Benchmark Integrity Audit

1. **Case Count & Identity:** Exactly 64 unique cases evaluated; no duplicate case IDs; no missing cases.
2. **Claim Count:** Exactly 136 claims evaluated across all 64 cases (100% extraction success).
3. **Ground Truth Distribution (Unchanged):**
   - **SUPPORTED:** 16 cases (25.0%)
   - **CONTRADICTED:** 23 cases (35.94%)
   - **UNVERIFIED:** 25 cases (39.06%)
   - **Total:** 64 cases (100.0%)

---

## 3. Provider Preflight Audit

Prior to the benchmark execution, provider reachability and credentials were confirmed:
- **NewsAPI Preflight:** HTTP 200 OK (1 preflight consumed, separate from the 99 benchmark request allowance)
- **Google Fact Check API Preflight:** HTTP 200 OK
- **Wikipedia General Reference Preflight:** HTTP 200 OK

---

## 4. Final Classification Metrics

### 3x3 Confusion Matrix

| Ground Truth \ Predicted | Pred SUPPORTED | Pred CONTRADICTED | Pred UNVERIFIED | Total |
| :--- | :---: | :---: | :---: | :---: |
| **GT SUPPORTED** | 0 | 2 | 14 | **16** |
| **GT CONTRADICTED** | 0 | 12 | 11 | **23** |
| **GT UNVERIFIED** | 0 | 6 | 19 | **25** |
| **Total Predicted** | **0** | **20** | **44** | **64** |

### Per-Class Performance

| Class | Ground Truth | Predicted | True Positives | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **SUPPORTED** | 16 | 0 | 0 | 0.00% | 0.00% | 0.00 |
| **CONTRADICTED** | 23 | 20 | 12 | 60.00% | 52.17% | 55.81 |
| **UNVERIFIED** | 25 | 44 | 19 | 43.18% | 76.00% | 55.07 |
| **Macro Average** | — | — | — | **34.39%** | **42.72%** | **36.96** |
| **Weighted Average** | — | — | — | **41.44%** | **48.44%** | **41.57** |

### False Positive & False Negative Rates by Class

| Metric | Calculation | Rate |
| :--- | :---: | :---: |
| **FPR for SUPPORTED** | 0 / (23 CONTRADICTED + 25 UNVERIFIED) = 0 / 48 | **0.00%** |
| **FPR for CONTRADICTED** | (2 GT SUPPORTED + 6 GT UNVERIFIED) / (16 + 25) = 8 / 41 | **19.51%** |
| **FNR for SUPPORTED** | (2 CONTRADICTED + 14 UNVERIFIED) / 16 GT SUPPORTED = 16 / 16 | **100.00%** |
| **FNR for CONTRADICTED** | (0 SUPPORTED + 11 UNVERIFIED) / 23 GT CONTRADICTED = 11 / 23 | **47.83%** |

---

## 5. Evidence & Provider Accounting

### Evidence by Provider
- **Google Fact Check API:** 22 items accepted (12.50% case hit rate)
- **NewsAPI (Live News):** 7 items accepted (9.38% case hit rate)
- **Wikipedia (General Reference):** 84 items accepted (60.94% case hit rate)
- **Total Accepted Evidence:** **113 items** (Relevance gate: 67.19% case relevance rate)

### Semantic Stance Breakdown
- **SUPPORTS:** 9 items (7.96%)
- **CONTRADICTS:** 40 items (35.40%)
- **NEUTRAL:** 64 items (56.64%)
- **Total:** 113 items (100.0%)

### NewsAPI Quota Accounting
- **Configured Benchmark Budget:** 99 requests max
- **Preflight Requests:** 1
- **Benchmark Requests Made:** 99
- **Total Outbound HTTP Requests:** 100
- **Claims Evaluated with NewsAPI:** 99
- **Claims Skipped (Budget Exhaustion):** 37
- **Provider Errors / 429 Responses:** 0 (cleanly governed)

---

## 6. Latency Profile

- **Mean Latency:** 2,190.42 ms
- **Median Latency:** 2,144.39 ms
- **P95 Latency:** 2,751.60 ms
- **Minimum Latency:** 846.71 ms
- **Maximum Latency:** 6,133.92 ms

---

## 7. Failure Taxonomy Breakdown

| Failure Category | Case Count | Description |
| :--- | :---: | :--- |
| **None (Correct)** | 31 | Correctly verified cases |
| **Fact-Check Retrieval Failure** | 10 | Benchmark claim lacked published fact-check in API index |
| **Live-News Retrieval Failure** | 9 | Supporting reporting was absent or unindexed by live provider |
| **Verdict Logic Error** | 5 | Ambiguous multi-evidence aggregation |
| **Ground Truth Ambiguity** | 3 | GT label differs from external reporting consensus |
| **Service Failure** | 3 | External provider rate-limit or network timeout during run |
| **Source Conflict** | 2 | Contradictory reporting across external sources |
| **Stance Error** | 1 | Sub-clause stance mismatch |
| **Claim Extraction Failure** | 0 | All claims successfully extracted |
| **Irrelevant Evidence** | 0 | No irrelevant evidence leaked past the gate |
| **Insufficient Evidence** | 0 | Handled through default unverified fallbacks |

---

## 8. Stage 42 Proposition-Matching Regression Observations

Explicit inspection of Stage 42 target cases and protections:

1. **5G / COVID-19 Proposition Matching (`fc_01`):**
   - Input: *"5G Radio Frequency Towers Cause and Transmit Viral Coronavirus Infections"*
   - Result: Correctly classified as **CONTRADICTED** (`is_correct: true`).
   - The aligned fact-check (*"No, 5G 'radiation' has NOT caused the second wave of COVID-19"*) was accepted with `CONTRADICTS` stance.
   - Generic COVID fact-checks (*"COVID-19 does not spread from person to person"*) were cleanly filtered at the gate, eliminating false conflicts.

2. **Apollo Numbered Entity Protection (`real_04`):**
   - Numbered mission entities (`Apollo 11`) correctly rejected adjacent mission articles (`Apollo 9`).

3. **Temporal Protection:**
   - Multi-year mismatches were rejected at the gate as expected.

---

## 9. Numerical Historical Comparison

| Metric | Stage 30 | Stage 34H | Stage 38 | Stage 40 | Stage 43 (Final) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total Cases** | 64 | 64 | 64 | 64 | **64** |
| **Correct Cases** | 29 | 33 | 26 | 30 | **31** |
| **Accuracy** | 45.31% | 51.56% | 40.62% | 46.88% | **48.44%** |
| **Macro F1** | 31.53 | 39.46 | 28.65 | 35.56 | **36.96** |
| **Weighted F1** | 35.81 | 44.32 | 32.54 | 40.03 | **41.57** |
| **CONTRADICTED Recall** | 26.09% | 65.22% | 26.09% | 47.83% | **52.17%** |
| **CONTRADICTED Precision**| 35.29% | 57.69% | 46.15% | 57.89% | **60.00%** |
| **CONTRADICTED F1** | 30.00 | 61.22 | 33.33 | 52.38 | **55.81** |
| **UNVERIFIED Recall** | 92.00% | 72.00% | 80.00% | 76.00% | **76.00%** |
| **UNVERIFIED Precision** | 48.94% | 47.37% | 39.22% | 42.22% | **43.18%** |
| **UNVERIFIED F1** | 63.89 | 57.14 | 52.63 | 54.29 | **55.07** |
| **SUPPORTED Recall** | 0.00% | 0.00% | 0.00% | 0.00% | **0.00%** |
| **Accepted Evidence** | 38 | 183 | 86 | 123 | **113** |
| **False CONTRADICTED** | — | 11 | 7 | 8 | **8** (2 from GT SUPPORTED, 6 from GT UNVERIFIED) |
| **Mean Latency** | — | 2,120 ms | — | 2,185 ms | **2,190 ms** |

---

## 10. Final Limitations & System Characteristics

1. **Free-Tier NewsAPI Daily Cap:** NewsAPI's 100 requests/day limit requires strict budgeting across 136 benchmark claims. Once 99 requests are consumed, remaining claims rely on Google Fact Check and Wikipedia Reference.
2. **SUPPORTED Recall Asymmetry:** Because live news and encyclopedic references prioritize neutral context rather than asserting definitive truth predicates, SUPPORTED ground-truth cases remain unverified in the absence of explicit corroborating fact checks.
3. **Index Temporal Lag:** Highly recent breaking claims depend on provider indexing latency.

---

## 11. Exact Artifact Paths

- **Raw Benchmark Results (Stage 43):** [`backend/evaluation/real_world_results_final_v4.json`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/evaluation/real_world_results_final_v4.json)
- **Evaluation Summary JSON (Stage 43):** [`backend/evaluation/stage_43_final_benchmark.json`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/evaluation/stage_43_final_benchmark.json)
- **Evaluation Report Markdown (Stage 43):** [`backend/evaluation/STAGE_43_FINAL_BENCHMARK.md`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/evaluation/STAGE_43_FINAL_BENCHMARK.md)
