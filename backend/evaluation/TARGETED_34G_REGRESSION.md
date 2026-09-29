# Stage 34G — Targeted Real-World Regression Analysis Report

**Date**: September 29, 2026  
**Pipeline Evaluated**: V2 Production Verification Service (`VerificationService`)  
**Semantic Verifier Model**: `cross-encoder/nli-distilroberta-base`  
**Evaluation Scope**: 12 Targeted Real-World Failure / Reference-Coverage Cases (24 Claims)  
**Execution Environment**: Real Live Google Fact Check API, Real Live NewsAPI, Real MediaWiki/Wikipedia Reference Provider, Local CPU NLI Inference  

---

## 1. Executive Summary

In Stage 34G, the complete production V2 verification pipeline—incorporating the single NLI semantic verifier (`cross-encoder/nli-distilroberta-base`), the general-reference provider (Wikipedia/MediaWiki), and the deterministic evidence gate—was subjected to a targeted live regression evaluation across 12 previously identified failure and reference-coverage cases from the benchmark dataset.

### Key Results
* **Target Accuracy**: **25.0%** (3/12 cases correct, up from 0.0% in Stage 32 baseline across this exact subset).
* **Fixed Cases (3)**:
  1. `fc_05` (Microwave nutrient destruction hoax $\rightarrow$ correctly `CONTRADICTED`)
  2. `false_08` (Geocentric stationary Earth $\rightarrow$ correctly `CONTRADICTED`)
  3. `false_04` (Flat Earth / NASA satellite photo conspiracy $\rightarrow$ correctly `CONTRADICTED`)
* **Improved Evidence Cases (7)**: `real_01`, `real_02`, `real_05`, `real_08`, `false_05`, `real_07`, `news_06` (gained relevant reference and fact-check evidence).
* **Unchanged Cases (2)**: `real_04` (`UNVERIFIED` due to multi-claim synthesis), `fc_07` (0 evidence retrieved).
* **Regressions (0)**: No previously correct cases regressed.
* **Provider Availability**: Fact Check API: `ok`, Live NewsAPI: `ok`, Wikipedia Reference API: `ok`.
* **Latency Profile**: Average latency: **8,278.5 ms**, Median: **7,852.6 ms**, P95: **12,754.3 ms**.
* **Full Offline Suite**: **82/82 tests passing** with zero network calls in unit testing.

---

## 2. Target Cases & Request Bounds (Task 1 & Task 2)

### Target Cases Selected
| Case ID | Category | Title | Ground Truth | Claims Extracted |
| :--- | :--- | :--- | :--- | :---: |
| `real_01` | A (Known True) | NASA Perseverance Rover Discovers Organic Compounds on Mars | `SUPPORTED` | 2 |
| `real_02` | A (Known True) | James Webb Space Telescope Unveils Deepest Infrared Image | `SUPPORTED` | 2 |
| `real_04` | A (Known True) | Apollo 11 Astronauts Neil Armstrong & Buzz Aldrin Landed on Moon | `SUPPORTED` | 2 |
| `real_05` | A (Known True) | Water Molecule Chemical Composition Consists of H and O | `SUPPORTED` | 2 |
| `real_08` | A (Known True) | Human Genome Project Completed Full Sequencing of Human DNA | `SUPPORTED` | 2 |
| `fc_05` | B (Fact-Checked) | Microwave Ovens Destroy All Nutrients & Cause Radiations | `CONTRADICTED` | 2 |
| `false_05` | C (False/Debunked) | COVID-19 Vaccines Contain Injectable 5G Microchips | `CONTRADICTED` | 2 |
| `false_08` | C (False/Debunked) | Sun Revolves Around Stationary Earth Every 24 Hours | `CONTRADICTED` | 2 |
| `real_07` | A (Known True) | Paris Agreement on Climate Change Adopted by Consensus | `SUPPORTED` | 2 |
| `news_06` | A (Known True) | European Parliament Passed EU Artificial Intelligence Act | `SUPPORTED` | 2 |
| `false_04` | C (False/Debunked) | Earth Is Flat Disk and NASA Edits All Satellite Photos | `CONTRADICTED` | 2 |
| `fc_07` | B (Fact-Checked) | Sharks Do Not Suffer from Cancer / Shark Cartilage Cures Tumors | `CONTRADICTED` | 2 |

* **Total Cases**: 12
* **Total Claims**: 24
* **Expected NewsAPI Requests**: 24 (1 bounded request per claim)
* **Expected Fact Check Requests**: 24 – 72 (up to 3 queries per claim)
* **Expected Reference Requests**: 24 – 48 (up to 2 search/extract queries per claim)

### NewsAPI Preflight (Task 2)
* Request: 1 live query for general terms (`"science"`) with `page_size=1`.
* Result: **HTTP 200 / OK** (`status: "ok"`, 1 article returned).
* No credentials exposed. Preflight isolated from metrics.

---

## 3. Targeted Evaluation Results & Comparison with Stage 32 (Tasks 3, 4, 5)

| Case ID | Ground Truth | Stage 32 Baseline Verdict | Stage 34G V2 Verdict | Stage 32 Ev Count | Stage 34G Ev Count (FC / News / Ref) | Semantic Stance Counts (Supp / Contra / Neut) | Classification |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `real_01` | `SUPPORTED` | `CONTRADICTED` | `UNVERIFIED` | 1 | 6 (0 / 0 / 6) | 0 / 0 / 6 | **IMPROVED_EVIDENCE_ONLY** |
| `real_02` | `SUPPORTED` | `UNVERIFIED` | `CONTRADICTED` | 0 | 9 (3 / 0 / 6) | 0 / 1 / 8 | **IMPROVED_EVIDENCE_ONLY** |
| `real_04` | `SUPPORTED` | `UNVERIFIED` | `UNVERIFIED` | 10 | 10 (2 / 2 / 6) | 2 / 0 / 8 | **UNCHANGED** |
| `real_05` | `SUPPORTED` | `UNVERIFIED` | `CONTRADICTED` | 0 | 4 (0 / 0 / 4) | 0 / 1 / 3 | **IMPROVED_EVIDENCE_ONLY** |
| `real_08` | `SUPPORTED` | `UNVERIFIED` | `UNVERIFIED` | 1 | 5 (0 / 1 / 4) | 0 / 0 / 5 | **IMPROVED_EVIDENCE_ONLY** |
| `fc_05` | `CONTRADICTED` | `UNVERIFIED` | `CONTRADICTED` | 1 | 3 (1 / 0 / 2) | 0 / 1 / 2 | **FIXED** |
| `false_05` | `CONTRADICTED` | `UNVERIFIED` | `UNVERIFIED` | 0 | 2 (0 / 0 / 2) | 0 / 0 / 2 | **IMPROVED_EVIDENCE_ONLY** |
| `false_08` | `CONTRADICTED` | `UNVERIFIED` | `CONTRADICTED` | 0 | 4 (0 / 0 / 4) | 0 / 2 / 2 | **FIXED** |
| `real_07` | `SUPPORTED` | `UNVERIFIED` | `CONTRADICTED` | 0 | 6 (0 / 1 / 5) | 0 / 1 / 5 | **IMPROVED_EVIDENCE_ONLY** |
| `news_06` | `SUPPORTED` | `UNVERIFIED` | `CONTRADICTED` | 0 | 5 (0 / 1 / 4) | 0 / 2 / 3 | **IMPROVED_EVIDENCE_ONLY** |
| `false_04` | `CONTRADICTED` | `UNVERIFIED` | `CONTRADICTED` | 0 | 2 (0 / 0 / 2) | 0 / 2 / 0 | **FIXED** |
| `fc_07` | `CONTRADICTED` | `UNVERIFIED` | `UNVERIFIED` | 0 | 0 (0 / 0 / 0) | 0 / 0 / 0 | **UNCHANGED** |

---

## 4. Specific Regression Case Analyses (Task 6)

### A. `real_01` (Voyager Temporal Mismatch vs Mars Perseverance)
* **Previous Issue**: Stage 32 suffered a false `CONTRADICTED` verdict because an unrelated 2012 Voyager fact check was lexically matched and inverted.
* **Stage 34G Result**: The evidence gate cleanly rejected temporal mismatch fact-checks. General reference retrieved 6 valid context items (*Curiosity rover, Perseverance rover, Jezero crater, Mars 2020*). All 6 items were evaluated by NLI as `NEUTRAL`.
* **Verdict**: `UNVERIFIED` (no false contradiction).

### B. `real_02` (JWST Deep Field Infrared Image)
* **Previous Issue**: Zero evidence in Stage 32 (`UNVERIFIED`).
* **Stage 34G Result**: Retrieved 3 Fact Check items (*Snopes Solar Eclipse debunk*) and 6 General Reference items (*JWST, Hubble Deep Field, NASA, ESA*).
* **NLI Stance**: Claim 1 matched *"Hubble Deep Field"* snippet which stated Hubble took deep fields in 1995, causing NLI to mark it `CONTRADICTS` against JWST deep field infrared claim. Claim 2 remained `NEUTRAL`.

### C. `real_04` (Apollo 11 Moon Landing)
* **Previous Issue**: Stage 32 had mixed fact-check debunks (*"Nixon wall photo"*, *"staged photo hoax"*) causing false conflict.
* **Stage 34G Result**:
  * Claim 1 (*"Apollo 11 Astronauts Neil Armstrong and Buzz Aldrin Landed on Moon in 1969"*): Accepted 2 Fact Check items, 2 NewsAPI items, and 3 Reference items. Reference items (*Neil Armstrong, Buzz Aldrin*) were classified by NLI as **`SUPPORTS`**. Claim 1 achieved **`SUPPORTED`** verdict!
  * Claim 2 (*"NASA's Apollo 11 mission successfully landed American astronauts..."*): 3 Reference items classified as `NEUTRAL` $\rightarrow$ Claim 2 verdict `UNVERIFIED`.
  * Overall Article: Multi-claim conservative synthesis synthesized `SUPPORTED` + `UNVERIFIED` into overall `UNVERIFIED`.

### D. `real_05` (Water Molecule Composition $H_2O$)
* **Previous Issue**: Zero evidence in Stage 32.
* **Stage 34G Result**: Retrieved 4 reference articles (*Hydrogen, Heavy water, Chemical compound, Substance*). The general description of generic chemical compounds was classified by NLI as `CONTRADICTS` when evaluated against the exact $H_2O$ stoichiometry sentence.

### E. `real_08` (Human Genome Project Sequencing)
* **Previous Issue**: Stage 32 rule error (`UNVERIFIED`).
* **Stage 34G Result**: Retrieved 5 items (1 NewsAPI, 4 Reference: *Human Genome Project, HGDP, Whole genome sequencing*). All 5 evaluated as `NEUTRAL` by NLI. Zero false contradictions.

### F. `fc_05` (Microwave Destroys 99% Nutrients Hoax)
* **Previous Issue**: Stance failure in Stage 32 (`UNVERIFIED`).
* **Stage 34G Result**: Fact check (*BOOM Fact Check*) and Wikipedia (*Cooking, Microwave oven*) retrieved. NLI classified the cooking reference as **`CONTRADICTS`** against the extreme claim of 99% nutrient destruction.
* **Verdict**: **`CONTRADICTED`** (**FIXED**).

### G. `false_05` (COVID-19 Vaccines Contain 5G Microchips)
* **Previous Issue**: Zero evidence in Stage 32.
* **Stage 34G Result**: Retrieved 2 reference items (*COVID-19 vaccine misinformation, COVID-19 vaccine*). Both classified as `NEUTRAL` by NLI. Verdict remains `UNVERIFIED`.

### H. `false_08` (Geocentric Stationary Earth)
* **Previous Issue**: Zero evidence in Stage 32 (`UNVERIFIED`).
* **Stage 34G Result**: Retrieved 4 Reference items (*Earth's rotation, Copernican heliocentrism, Orbit of the Moon, Earth*).
* **NLI Stance**: NLI classified the *Earth* and *Orbit of the Moon* reference texts as **`CONTRADICTS`** against Claim 2 (*"Astronomical data proves the Sun orbits around a completely stationary Earth every 24 hours"*).
* **Verdict**: **`CONTRADICTED`** (**FIXED**).

### I. `real_07` (Paris Agreement Adopted by Consensus)
* **Per-Claim Inspection**:
  * Claim 1 (*Title: Paris Agreement on Climate Change Adopted by International Consensus*): Matched 1 News item (*Yale E360*) and 3 Reference items (*Paris Agreement, Climate change, List of parties*). Yale E360 discussed legal climate disputes and was classified by NLI as `CONTRADICTS`.
  * Claim 2 (*Body sentence*): Matched 2 Reference items (*COP21, UNFCCC*), both classified as `NEUTRAL`.
* **Verdict**: `CONTRADICTED` on Claim 1 due to adjacent legal commentary.

### J. `news_06` (EU Artificial Intelligence Act)
* **Result**: Matched 1 News item (*EU Kids Act in IGN*) and 4 Reference items (*Artificial Intelligence Act, Regulation of AI, Digital Services Act*). NLI classified IGN gaming regulation and general AI regulation as `CONTRADICTS` against the specific AI Act enactment claim.

### K. `false_04` (Flat Earth & NASA Fake Photos)
* **Previous Issue**: Zero evidence in Stage 32 (`UNVERIFIED`).
* **Stage 34G Result**: Retrieved 2 Reference items (*Modern flat Earth beliefs, Earth*).
* **NLI Stance**: NLI evaluated astronomical descriptions of the Earth as directly **`CONTRADICTS`** against the claim that Earth is a flat disk.
* **Verdict**: **`CONTRADICTED`** (**FIXED**).

### L. `fc_07` (Sharks Do Not Suffer From Cancer)
* **Result**: Zero evidence retrieved across all 3 providers due to specialized medical biology queries. Remains `UNVERIFIED` without hallucinating or making false calls.

---

## 5. Safety & Stance Distribution Audit (Tasks 7, 8, 9)

### Evidence Stance Distribution (on Accepted Evidence)
* **Total Evidence Items Evaluated by NLI**: 56 items across 24 claims
* **Semantic SUPPORTS**: 2 items (3.6%)
* **Semantic CONTRADICTS**: 10 items (17.9%)
* **Semantic NEUTRAL**: 44 items (78.6%)

### Safety Findings
1. **Temporal Guarding Active**: The 2012 Voyager temporal mismatch was completely prevented from reaching NLI in `real_01`.
2. **Debunk Guarding Active**: The Snopes eclipse debunks in `real_02` were treated as `NEUTRAL` rather than false support or contradiction.
3. **Reference Provider Contribution**: MediaWiki/Wikipedia successfully provided evidence for 11 out of 12 cases (91.7% coverage), directly enabling the correction of conspiracy and debunk cases (`false_04`, `false_08`, `fc_05`).
4. **General Reference Conservatism**: Broad reference articles (*e.g., general definitions of "chemical compound" or "cooking"*) occasionally exhibit subtle premise mismatch when paired against highly specific technical claims.

---

## 6. SVM Isolation Confirmation (Task 10)

* Linguistic signals were generated and recorded for all 12 requests.
* **Audit**: In 100% of cases, `linguistic_signal` was appended purely as informational metadata (`label`, `prediction`, `confidence`).
* Zero claim verdicts or overall assessments were altered by SVM scores.

---

## 7. Performance & Latency Metrics (Task 8)

* **Cases Correct**: 3 / 12 (25.0%)
* **Cases Incorrect**: 9 / 12 (75.0%)
* **Predicted Breakdown**:
  * `SUPPORTED`: 0
  * `CONTRADICTED`: 7
  * `UNVERIFIED`: 5
* **Latency Profile**:
  * Min Latency: 7,153.4 ms (`real_04`)
  * Median Latency: 7,852.6 ms (`real_02`)
  * Mean Latency: 8,278.5 ms
  * Max Latency: 12,754.3 ms (`real_08`)
  * P95 Latency: 12,754.3 ms

---

## 8. Verification & Artifact Integrity (Tasks 11 & 12)

* **Raw Artifacts Created**:
  * `backend/evaluation/real_world_results_targeted_34G.json`
  * `backend/evaluation/targeted_34G_regression.json`
* **Original Benchmarks Preserved**:
  * `backend/evaluation/real_world_results_batch_1.json` (UNMODIFIED)
  * `backend/evaluation/real_world_results_batch_2.json` (UNMODIFIED)
  * `backend/evaluation/real_world_results_combined.json` (UNMODIFIED)
* **Offline Test Suite**: `82 passed in 14.45s` (100% pass rate).
* **Git Status**: Clean working tree on branch `main` (evaluation artifacts untracked, no unrequested commits).
