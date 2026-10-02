# Stage 40 — Final 64-Case Real-World Benchmark Report

## 1. Executive Overview

The Stage 40 final real-world benchmark was executed against the full 64-case / 136-claim dataset using the production V2 verification pipeline with quota-safe NewsAPI request budgeting.

### Key Numerical Results

- **Total Cases Evaluated:** 64
- **Total Claims Extracted:** 136
- **Overall Accuracy:** 46.88% (30 / 64 correct)
- **Macro F1:** 35.56
- **Weighted F1:** 40.03
- **CONTRADICTED Precision / Recall / F1:** 57.89% / 47.83% / 52.38
- **UNVERIFIED Precision / Recall / F1:** 42.22% / 76.00% / 54.29
- **SUPPORTED Precision / Recall / F1:** 0.00% / 0.00% / 0.00
- **False Positive Rate for CONTRADICTED:** 19.51% (8 / 41 non-CONTRADICTED cases predicted as CONTRADICTED)
- **False Negative Rate for CONTRADICTED:** 52.17% (12 / 23 CONTRADICTED cases not predicted as CONTRADICTED)
- **False Negative Rate for SUPPORTED:** 100.00% (16 / 16 SUPPORTED cases not predicted as SUPPORTED)
- **Conflict Rate:** 4.69% (3 cases)

---

## 2. 3x3 Confusion Matrix

| Ground Truth \ Predicted | Predicted SUPPORTED | Predicted CONTRADICTED | Predicted UNVERIFIED | Row Total |
| :--- | :---: | :---: | :---: | :---: |
| **GT SUPPORTED** | 0 | 2 | 14 | **16** |
| **GT CONTRADICTED** | 0 | 11 | 12 | **23** |
| **GT UNVERIFIED** | 0 | 6 | 19 | **25** |
| **Column Total** | **0** | **19** | **45** | **64** |

---

## 3. NewsAPI Quota-Safe Request Accounting

The Stage 40 benchmark operated under an explicit NewsAPI quota budget constraint:
- **NewsAPI Preflight Requests:** 1 (HTTP 200 OK)
- **Benchmark Request Budget:** 99 requests
- **Benchmark Requests Made:** 99 requests
- **Total NewsAPI Requests (Preflight + Benchmark):** 100 requests
- **Claims Evaluated with NewsAPI:** 99 claims
- **Claims Skipped (Budget Exhaustion):** 37 claims
- **Budget Exhaustion Encountered:** True (at claim 100)
- **Provider HTTP 429 Errors:** 0

> [!NOTE]
> Due to the NewsAPI Developer 100 req/day allowance, the first 99 claims were queried with live NewsAPI retrieval. The remaining 37 claims were evaluated using Google Fact Check API and Wikipedia Reference retrieval only. Provider availability was tracked and recorded transparently per claim.

- **Google Fact Check API Requests:** 136 claims
- **Wikipedia Reference Requests:** 136 claims

---

## 4. Evidence Retrieval & Semantic Relations

- **Total Accepted Evidence Items:** 123
  - **Google Fact Check API:** 29 items (23.58%)
  - **Live News (NewsAPI):** 8 items (6.50%)
  - **General Reference (Wikipedia):** 86 items (69.92%)
- **Semantic Stance Classifications:**
  - `SUPPORTS`: 10 items (8.13%)
  - `CONTRADICTS`: 45 items (36.59%)
  - `NEUTRAL`: 68 items (55.28%)

---

## 5. Latency Distribution

- **Mean Response Time:** 3,304.48 ms
- **Median Response Time:** 3,159.66 ms
- **P95 Response Time:** 4,943.43 ms
- **Minimum Response Time:** 924.37 ms
- **Maximum Response Time:** 7,630.32 ms

---

## 6. Numerical Comparison Across Stages

| Metric | Stage 30 Baseline | Stage 34H (Pre-Gate) | Stage 38 (Post-37 Gate) | Stage 40 (Final V2) |
| :--- | :---: | :---: | :---: | :---: |
| **Cases** | 64 | 64 | 64 | 64 |
| **Claims** | 136 | 136 | 136 | 136 |
| **Accuracy** | 45.31% (29/64) | 51.56% (33/64) | 40.62% (26/64) | **46.88% (30/64)** |
| **CONTRADICTED Recall** | 26.09% | 65.22% (15/23) | 26.09% (6/23) | **47.83% (11/23)** |
| **CONTRADICTED Precision** | — | 57.69% | 46.15% | **57.89% (11/19)** |
| **CONTRADICTED F1** | — | 61.22 | 33.33 | **52.38** |
| **UNVERIFIED Recall** | 92.00% | 72.00% (19/25) | 80.00% (20/25) | **76.00% (19/25)** |
| **UNVERIFIED Precision** | — | 47.37% | 39.22% | **42.22% (19/45)** |
| **UNVERIFIED F1** | — | 57.14 | 52.63 | **54.29** |
| **SUPPORTED Recall** | 0.00% (0/16) | 0.00% (0/16) | 0.00% (0/16) | **0.00% (0/16)** |
| **SUPPORTED Precision** | 0.00% | 0.00% | 0.00% | **0.00%** |
| **SUPPORTED F1** | 0.00 | 0.00 | 0.00 | **0.00** |
| **Macro F1** | 31.53 | 39.46 | 28.65 | **35.56** |
| **Weighted F1** | 35.81 | 44.32 | 32.54 | **40.03** |
| **Accepted Evidence** | 38 | 183 | 86 | **123** |
| **False Contradictions** | — | 11 | 7 | **8** |

---

## 7. Stage 39 Recovery Observations

1. **Adjacent Entity & Mission Leakage:**
   - Case `fc_06` (Apollo 11 moon landing moon-rock claim) correctly matched proposition-level Wikipedia evidence and evaluated as `CONTRADICTED` without cross-mission distortion.
2. **Temporal Mismatch Protection:**
   - Historical cases (`real_01`–`real_08`) and synthetic items preserved temporal checks without false contradiction classifications from recent event timestamps.
3. **Fact-Check Rating Preservation:**
   - Cases `fc_01` (Jana Gana Mana UNESCO hoax) and `fc_04` (drinking water COVID cure) preserved external fact-checker verdict alignments, evaluating as `CONTRADICTED`.
4. **Evidence Volume & Specificity Trade-Off:**
   - Total accepted evidence was 123 items in Stage 40 compared to 86 items in Stage 38 and 183 items in Stage 34H.
   - CONTRADICTED recall was 47.83% (11/23) in Stage 40 compared to 26.09% (6/23) in Stage 38 and 65.22% (15/23) in Stage 34H.
   - False contradictions were 8 cases in Stage 40 compared to 7 cases in Stage 38 and 11 cases in Stage 34H.

---

## 8. Failure Taxonomy Breakdown

- **None (Correct Assessment):** 30 cases (46.88%)
- **Fact-Check Retrieval Failure (No external fact check matched):** 11 cases (17.19%)
- **Live News Retrieval Failure (No supporting live news retrieved):** 8 cases (12.50%)
- **Verdict Logic / Aggregation Limit:** 5 cases (7.81%)
- **Ground-Truth Ambiguity:** 3 cases (4.69%)
- **Service Failure (NewsAPI quota exhaustion on later claims):** 3 cases (4.69%)
- **Stance Error:** 2 cases (3.12%)
- **Source Conflict:** 2 cases (3.12%)
- **Claim Extraction Failure:** 0 cases (0.00%)
- **Irrelevant Evidence:** 0 cases (0.00%)

---

## 9. Final Integrity Verification

- **Total Cases:** 64
- **Ground Truth Distribution:** 16 SUPPORTED / 23 CONTRADICTED / 25 UNVERIFIED
- **Predicted Distribution:** 0 SUPPORTED / 19 CONTRADICTED / 45 UNVERIFIED
- **Total Claims Extracted:** 136
- **NewsAPI Preflight Count:** 1
- **NewsAPI Benchmark Request Count:** 99
- **NewsAPI Total Request Count:** 100
- **Duplicate Cases / Claims:** 0
- **Production Code Changes:** 0
- **Dataset / Ground Truth Modifications:** 0
- **Historical Result Overwrites:** 0
