# Stage 38 — Post-Stage-37 Real-World Re-Evaluation Report

**Date**: September 30, 2026  
**Evaluation Target**: Production V2 Verification Pipeline post-Stage-37 Evidence Specificity Changes  
**Pipeline Architecture**:
- Multi-Claim Extractor (`ClaimExtractor`)
- Multi-Source Concurrent Retrieval: Google Fact Check API + NewsAPI + Wikipedia Reference Provider
- Hardened Evidence Relevance Gate (`EvidenceMatcher`)
- Single Semantic NLI Verifier (`cross-encoder/nli-distilroberta-base`)
- Deterministic Directional Evidence Aggregator (`EvidenceAggregator`)
- Deterministic Verdict Policy Engine (`VerdictEngine`)
- Informational LinearSVM Signal (`SVMPipelineIntegrator`)

---

## 1. Benchmark Integrity & Provider Preflight

### Benchmark Integrity
- **Total Cases**: 64
- **Total Extracted Claims**: 136
- **Unique Case IDs**: 64 (0 duplicate IDs, 0 missing IDs)
- **Ground Truth Distribution**:
  - `SUPPORTED`: 16 cases (25.0%)
  - `CONTRADICTED`: 23 cases (35.94%)
  - `UNVERIFIED`: 25 cases (39.06%)
- **Dataset Mutation**: 0 modifications to `backend/evaluation/real_world_dataset.json`.

### Provider Preflight (Isolated Execution)
Prior to benchmark execution, one preflight query was issued to each configured provider:
- **Google Fact Check API**: `OK` (3 items returned)
- **NewsAPI**: `OK` (5 items returned)
- **Wikipedia Reference Provider**: `OK` (3 items returned)
- **Preflight Isolation**: Preflight requests were recorded separately and excluded from benchmark request accounting.

---

## 2. Quantitative Evaluation Metrics

### Core Benchmark Metrics

| Metric | Stage 38 Post-37 Value |
| :--- | :---: |
| **Total Cases Evaluated** | 64 |
| **Total Claims Evaluated** | 136 |
| **Correct Predictions** | 26 |
| **Incorrect Predictions** | 38 |
| **Overall Accuracy** | **40.62%** (26 / 64) |
| **Macro F1 Score** | **28.65%** |
| **Weighted F1 Score** | **32.54%** |
| **UNVERIFIED Rate** | 79.69% (51 / 64) |
| **Conflict Rate** | 0.00% (0 / 64) |
| **Provider Availability** | 100.0% (`fact_check_api`: ok, `live_news_api`: ok, `reference_api`: ok) |

### Per-Class Performance Breakdown

| Class | Precision | Recall | F1 Score | Ground Truth Support | True Positives | False Positives | False Negatives |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SUPPORTED** | 0.00% | 0.00% | 0.00% | 16 | 0 | 0 | 16 |
| **CONTRADICTED** | 46.15% | 26.09% | 33.33% | 23 | 6 | 7 | 17 |
| **UNVERIFIED** | 39.22% | 80.00% | 52.63% | 25 | 20 | 31 | 5 |

---

## 3. Confusion Matrix & Error Rates

### 3x3 Confusion Matrix (Ground Truth Rows vs. Predicted Columns)

$$\begin{array}{|l|c|c|c|c|}
\hline
\textbf{Ground Truth} & \textbf{Pred: SUPPORTED} & \textbf{Pred: CONTRADICTED} & \textbf{Pred: UNVERIFIED} & \textbf{Total (GT)} \\ \hline
\textbf{SUPPORTED} & 0 & 2 & 14 & \mathbf{16} \\ \hline
\textbf{CONTRADICTED} & 0 & 6 & 17 & \mathbf{23} \\ \hline
\textbf{UNVERIFIED} & 0 & 5 & 20 & \mathbf{25} \\ \hline
\textbf{Total (Predicted)} & \mathbf{0} & \mathbf{13} & \mathbf{51} & \mathbf{64} \\ \hline
\end{array}$$

### Error Rates
* **False Positive Rate for SUPPORTED**: 0.00% (0 / 48 non-supported cases predicted as SUPPORTED)
* **False Positive Rate for CONTRADICTED**: 17.07% (7 / 41 non-contradicted cases predicted as CONTRADICTED)
* **False Negative Rate for CONTRADICTED**: 73.91% (17 / 23 contradicted cases predicted as non-contradicted)
* **False Negative Rate for SUPPORTED**: 100.00% (16 / 16 supported cases predicted as non-supported)

---

## 4. Evidence & Semantic Breakdown

### Accepted Evidence Items by Provider
* **Total Accepted Evidence Items**: **86**
  * **Google Fact Check API**: 23 items (26.74%)
  * **NewsAPI**: 5 items (5.81%)
  * **General Reference (Wikipedia)**: 58 items (67.44%)

### Semantic Relation Distribution (NLI Inferences on Accepted Evidence)
* **Semantic SUPPORTS**: 10 items (11.63%)
* **Semantic CONTRADICTS**: 21 items (24.42%)
* **Semantic NEUTRAL**: 55 items (63.95%)
* **Total Evaluated Evidence Items**: 86 items

---

## 5. Latency Profile

*End-to-end wall clock latency across all 64 live benchmark cases (excluding preflight requests).*

* **Mean Latency**: **2,955.24 ms**
* **Median Latency**: **2,812.87 ms**
* **P95 Latency**: **4,763.09 ms**
* **Minimum Latency**: 851.45 ms (`unver_05`)
* **Maximum Latency**: 8,271.35 ms (`unver_03`)

---

## 6. Request Accounting

| Provider | Preflight Requests | Benchmark Requests | Total Live Calls | Rate Limit Events | HTTP Failures |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Google Fact Check** | 1 | 4 | 5 | 0 | 0 |
| **NewsAPI** | 1 | 1 | 2 | 0 | 0 |
| **Wikipedia Reference** | 1 | 461 | 462 | 0 | 0 |

---

## 7. Failure Taxonomy Breakdown

| Failure Classification | Case Count | Percentage of Failures (38 Total) | Description |
| :--- | :---: | :---: | :--- |
| **Insufficient Evidence** | 22 | 57.89% | No external evidence retrieved; system outputs `UNVERIFIED` (e.g. `fc_02`, `fc_07`, `false_04`, `synth_02`, `unver_04`). |
| **Multi-Claim Synthesis Limitation** | 8 | 21.05% | In multi-claim articles, one claim is unverified or neutral while companion claim is factual, resulting in overall `UNVERIFIED`. |
| **Service Failure / Retrieval Timeout** | 4 | 10.53% | Upstream external search provider returned empty results or timed out under live concurrency. |
| **Semantic Premise Conflict** | 3 | 7.89% | NLI evaluated premise as contradictory due to subtle numeric or phrasing divergence (e.g. `real_04`, `news_06`, `synth_08`). |
| **Source Conflict** | 1 | 2.63% | Competing retrieved sources provided opposing signals (`real_03`). |
| **Correct Cases (No Failure)** | 26 | — | Matched ground truth label. |

---

## 8. Numerical Comparison with Stage 34H and Stage 30 Baseline

| Metric | Stage 30 Baseline | Stage 34H Final V2 | Stage 38 Post-37 | Difference (St. 38 vs St. 34H) | Difference (St. 38 vs St. 30) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total Cases** | 64 | 64 | 64 | 0 | 0 |
| **Total Claims** | 136 | 136 | 136 | 0 | 0 |
| **Correct Cases** | 29 | 33 | 26 | -7 | -3 |
| **Overall Accuracy** | 45.31% | 51.56% | 40.62% | -10.94% | -4.69% |
| **Macro F1 Score** | 31.53% | 39.46% | 28.65% | -10.81% | -2.88% |
| **Weighted F1 Score** | 35.81% | 44.32% | 32.54% | -11.78% | -3.27% |
| **Supported Recall** | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| **Contradicted Recall** | 26.09% | 65.22% | 26.09% | -39.13% | 0.00% |
| **Contradicted Precision** | 50.00% | 57.69% | 46.15% | -11.54% | -3.85% |
| **Unverified Recall** | 92.00% | 72.00% | 80.00% | +8.00% | -12.00% |
| **Unverified Precision** | 45.10% | 47.37% | 39.22% | -8.15% | -5.88% |
| **False CONTRADICTED Count** | 6 | 11 | 7 | -4 (-36.36%) | +1 |
| **FPR for CONTRADICTED** | 14.63% | 26.83% | 17.07% | -9.76% | +2.44% |
| **Accepted Evidence Items** | 38 | 183 | 86 | -97 (-53.01%) | +48 |
| **Mean Latency** | 3,854.98 ms | 8,113.30 ms | 2,955.24 ms | -5,158.06 ms (-63.58%) | -899.74 ms (-23.34%) |
| **Median Latency** | — | 7,799.20 ms | 2,812.87 ms | -4,986.33 ms (-63.93%) | — |
| **P95 Latency** | — | 12,212.40 ms | 4,763.09 ms | -7,449.31 ms (-61.00%) | — |

---

## 9. Stage 37 Regression Observations

1. **Reduction in False Contradictions from Adjacent Entities**:
   - In Stage 34H, 11 non-contradicted cases were falsely predicted as `CONTRADICTED` due to adjacent topic leakage (e.g. `Apollo 9` / `Apollo 8` matching for `Apollo 11`, `real_02` JWST, `real_05` water molecule, `real_06` Higgs boson, and `synth_03`).
   - In Stage 38, false contradictions dropped from 11 to 7, with `real_02`, `real_05`, `real_06`, and `synth_03` resolved to non-contradicted outcomes.
2. **Evidence Filtering Granularity**:
   - Total evidence items passing the relevance gate reduced from 183 in Stage 34H to 86 in Stage 38. Broad unaligned multi-paragraph texts are filtered out before NLI inference.
3. **SUPPORTED Recall Observation**:
   - `SUPPORTED` recall remains at 0.00% across the benchmark. While focused reference passages now produce high semantic entailment (79.3%–98.3%) on exact proposition matches in unit tests, in the full benchmark multi-claim articles require all companion claims to be verified. When one companion claim receives neutral or no evidence, the article verdict defaults to `UNVERIFIED`.
4. **Latency Profile**:
   - Mean latency decreased from 8,113.30 ms to 2,955.24 ms, and P95 latency decreased from 12,212.40 ms to 4,763.09 ms.

---

## 10. Remaining Limitations

1. **Multi-Claim Conservative Synthesis**: Multi-claim articles default to `UNVERIFIED` when one claim lacks external evidence, even if another claim has verified supporting evidence.
2. **Date Specificity Divergence**: Wikipedia lead extracts often state the year of an event while omitting the exact day/month, leading NLI to classify the relationship as `NEUTRAL` rather than `SUPPORTS` when claims specify full dates.
3. **Single Semantic Model Constraint**: No secondary models or LLMs were added, adhering strictly to the architectural constraints.

---

## 11. Artifacts Generated

- **Raw Benchmark Results**: [real_world_results_post37.json](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/evaluation/real_world_results_post37.json)
- **Summary Metrics JSON**: [stage_38_post37_reevaluation.json](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/evaluation/stage_38_post37_reevaluation.json)
- **Markdown Report**: [STAGE_38_POST37_REEVALUATION.md](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/evaluation/STAGE_38_POST37_REEVALUATION.md)
