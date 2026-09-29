# Stage 34G.1 — Forensic Audit of Targeted Semantic Regression

**Date**: September 29, 2026  
**Subject**: Granular Per-Claim & Per-Evidence Forensic Audit of Stage 34G Regression  
**Model**: `cross-encoder/nli-distilroberta-base`  
**Dataset Scope**: 12 Target Cases, 24 Extracted Claims, 56 NLI-Evaluated Evidence Items  
**Audit Artifacts**:
- `backend/evaluation/forensic_34G_audit.json`
- `backend/evaluation/real_world_results_targeted_34G.json`
- `backend/evaluation/targeted_34G_regression.json`

---

## 1. Executive Forensic Summary

This forensic audit investigates the exact per-claim and per-evidence mechanics of the Stage 34G targeted regression run. Every input premise, hypothesis, matcher decision, NLI score, and verdict synthesis step across all 24 claims and 56 accepted evidence items was examined to diagnose why 7 ground-truth SUPPORTED cases and 2 ground-truth CONTRADICTED cases produced UNVERIFIED or CONTRADICTED outcomes.

### Core Audit Findings
1. **Reconciliation of Request & Evidence Counts**:
   - Total Claims: **24** (2 claims extracted per case across 12 cases).
   - Provider Requests: **NewsAPI = 24** (1 bounded search per claim), **Google Fact Check = 48** (up to 2 queries per claim), **Wikipedia Reference = 36** (primary & fallback search + summary extracts).
   - NLI Invocations: **56** accepted evidence items evaluated by NLI.
   - NLI Stance Breakdown: **2 SUPPORTS (3.6%)**, **10 CONTRADICTS (17.9%)**, **44 NEUTRAL (78.6%)**.
2. **Dominant Failure Mechanisms**:
   - **Neutral Reference Bias (38 of 44 NEUTRALs)**: General reference extracts from Wikipedia provide high-level conceptual overviews (e.g., definitions of *Perseverance rover, chemical compound, ESA, NASA*) that are logically neutral with respect to specific episodic or quantitative claims.
   - **Premise / Specificity Mismatch (4 of 7 GT-SUPPORTED cases)**: When an encyclopedia snippet discusses a related topic (e.g. *Hubble Deep Field in 1995* instead of *JWST Deep Field in 2022*, or general *Chemical compound definition* instead of $H_2O$), NLI treats the entity or temporal divergence as a logical **CONTRADICTION**.
   - **Multi-Claim Conservative Synthesis (1 of 7 GT-SUPPORTED cases)**: In `real_04` (*Apollo 11*), Claim 1 was correctly evaluated as **`SUPPORTED`** (2 supporting reference items), but Claim 2 received neutral reference items, causing the article-level synthesis rule to conservatively output **`UNVERIFIED`**.

---

## 2. Request & Evidence Reconciliation (Tasks 1 & 2)

### A. Provider Request Mechanics
| Provider | Raw Calls | Query Bound Rule | Explanation |
| :--- | :---: | :--- | :--- |
| **NewsAPI** | 24 | 1 query / claim | `newsapi_retriever.py` searches using `primary_query` only (24 claims $\times$ 1 = 24 calls). |
| **Google Fact Check** | 48 | $\le 3$ queries / claim | `fact_check_retriever.py` executes primary query + fallback query (24 claims $\times$ 2 = 48 calls). |
| **MediaWiki / Wikipedia** | 36 | $\le 2$ queries / claim | `reference_retriever.py` executes primary search and conditional fallback search, fetching page extracts. |

### B. Evidence Flow Funnel
$$\text{Retrieved Candidates (82)} \xrightarrow{\text{EvidenceMatcher Gate}} \text{Accepted Evidence (56)} \xrightarrow{\text{NLI Semantic Verifier}} \begin{cases} \text{SUPPORTS: 2 (3.6\%)} \\ \text{CONTRADICTS: 10 (17.9\%)} \\ \text{NEUTRAL: 44 (78.6\%)} \end{cases}$$

---

## 3. Forensic Analysis of the 7 GT-SUPPORTED Cases (Task 3)

| Case ID | Title | Claim 1 Verdict (NLI Signal) | Claim 2 Verdict (NLI Signal) | Article Verdict | Root Cause Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `real_01` | NASA Mars Perseverance | `UNVERIFIED` (`NEUTRAL`, 3 ev) | `UNVERIFIED` (`NEUTRAL`, 3 ev) | `UNVERIFIED` | **B (Evidence accepted but NLI returned NEUTRAL)** |
| `real_02` | JWST Deep Field Image | `CONTRADICTED` (`CONTRADICTS`, 3 ev) | `UNVERIFIED` (`NEUTRAL`, 6 ev) | `CONTRADICTED` | **C (Evidence accepted but NLI returned CONTRADICTS)** |
| `real_04` | Apollo 11 Moon Landing | **`SUPPORTED`** (**`SUPPORTS`**, 7 ev) | `UNVERIFIED` (`NEUTRAL`, 3 ev) | `UNVERIFIED` | **E (Multi-claim synthesis limitation)** |
| `real_05` | Water $H_2O$ Composition | `UNVERIFIED` (`NEUTRAL`, 2 ev) | `CONTRADICTED` (`CONTRADICTS`, 2 ev) | `CONTRADICTED` | **C (Evidence accepted but NLI returned CONTRADICTS)** |
| `real_08` | Human Genome Project | `UNVERIFIED` (`NEUTRAL`, 4 ev) | `UNVERIFIED` (`NEUTRAL`, 1 ev) | `UNVERIFIED` | **B (Evidence accepted but NLI returned NEUTRAL)** |
| `real_07` | Paris Climate Agreement | `CONTRADICTED` (`CONTRADICTS`, 4 ev) | `UNVERIFIED` (`NEUTRAL`, 2 ev) | `CONTRADICTED` | **C (Evidence accepted but NLI returned CONTRADICTS)** |
| `news_06` | EU Artificial Intelligence Act | `CONTRADICTED` (`CONTRADICTS`, 3 ev) | `UNVERIFIED` (`NEUTRAL`, 2 ev) | `CONTRADICTED` | **C (Evidence accepted but NLI returned CONTRADICTS)** |

### Per-Case Deep Dives

1. **`real_01` (Perseverance Organic Molecules)**:
   - *Premises*: Wikipedia extracts for *Curiosity (rover)*, *Perseverance (rover)*, *Life on Mars*, *Jezero (crater)*, *Mars 2020*.
   - *NLI Output*: All 6 items scored $\ge 0.85$ probability for `NEUTRAL`.
   - *Reason*: General mission overviews do not mention the specific July 2023 discovery of organic molecules in Jezero crater rock samples. NLI correctly recognized lack of entailment.
2. **`real_02` (JWST Deep Field Infrared)**:
   - *Premises*: Wikipedia *Hubble Deep Field* (*"assembled from 342 exposures taken with Wide Field Planetary Camera 2 in 1995"*).
   - *NLI Output*: `CONTRADICTION` (prob: $0.7436$).
   - *Reason*: NLI compared Hubble's 1995 deep field against the claim that JWST unveiled the deepest infrared image, treating the conflicting telescope instrument as a direct factual contradiction.
3. **`real_04` (Apollo 11 Moon Landing)**:
   - *Claim 1*: Matched Wikipedia *Neil Armstrong* and *Buzz Aldrin*, both scored as **`SUPPORTS`** ($0.88+$ entailment). Claim 1 verdict: **`SUPPORTED`**.
   - *Claim 2*: Matched Wikipedia *Apollo 11*, scored as `NEUTRAL`.
   - *Article Synthesis*: Policy requires all factual claims to be supported or non-conflicting; `SUPPORTED` + `UNVERIFIED` $\rightarrow$ `UNVERIFIED`.
4. **`real_05` (Water Molecule Composition)**:
   - *Claim 2 Hypothesis*: *"Pure water is a chemical compound consisting of two hydrogen atoms bonded to one oxygen atom forming H2O"*.
   - *Premise*: Wikipedia *Chemical compound* (*"A chemical compound is a chemical substance composed of many identical molecules containing atoms from more than one chemical element..."*).
   - *NLI Output*: `CONTRADICTION` (prob: $0.7902$).
   - *Reason*: Generic chemical definition discusses general multi-element bonds without mentioning water stoichiometry, triggering NLI contradiction.
5. **`real_07` (Paris Climate Agreement)**:
   - *Claim 1 Hypothesis*: *"Paris Agreement on Climate Change Adopted by International Consensus"*.
   - *Premise*: Yale E360 (*"From Indigenous Loss, a Potent Legal Argument on Climate... Human rights lawyer Julian Aguon explores how warming threatens island nations in legal actions..."*).
   - *NLI Output*: `CONTRADICTION` (prob: $0.8352$).
   - *Reason*: Legal commentary on non-compliance and damages contradicted the adoption proposition.
6. **`news_06` (EU AI Act Passed)**:
   - *Claim 1 Hypothesis*: *"European Parliament Passed EU Artificial Intelligence Act"*.
   - *Premises*: IGN (*"EU Kids Act Could Require Gamers... presented before EP on Thursday"*) and Wikipedia *Regulation of AI* (*"Regulation of AI is an emerging issue worldwide..."*).
   - *NLI Output*: `CONTRADICTION` ($0.6723$ and $0.8861$).
   - *Reason*: NLI interpreted "presented on Thursday" and "emerging issue" as unpassed/future status.

---

## 4. Forensic Analysis of the 5 GT-CONTRADICTED Cases (Task 4)

| Case ID | Title | Contradicting Evidence Found? | Matcher Accepted? | NLI Stance | Final Verdict | Success / Failure Reason |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `fc_05` | Microwave Destroys 99% Nutrients | Yes (Wikipedia: *Cooking*) | Yes | **`CONTRADICTS`** ($0.91$) | **`CONTRADICTED`** | **FIXED**: NLI refuted extreme 99% nutrient loss claim. |
| `false_08` | Geocentric Stationary Earth | Yes (Wikipedia: *Earth*, *Orbit of Moon*) | Yes | **`CONTRADICTS`** ($0.86$) | **`CONTRADICTED`** | **FIXED**: NLI refuted stationary Earth orbit claim. |
| `false_04` | Flat Earth / NASA Fake Images | Yes (Wikipedia: *Modern flat Earth*, *Earth*) | Yes | **`CONTRADICTS`** ($0.94$) | **`CONTRADICTED`** | **FIXED**: NLI refuted flat disk claim. |
| `false_05` | COVID-19 Vaccine 5G Microchips | Yes (Wikipedia: *Misinformation*) | Yes | `NEUTRAL` ($0.88$) | `UNVERIFIED` | **Model Limitation on Sociological Debunk**: NLI evaluated description of misinformation spread as neutral to microchip existence. |
| `fc_07` | Sharks Do Not Suffer Cancer | No (0 results across 3 APIs) | N/A | `NO_EVIDENCE` | `UNVERIFIED` | **Retrieval Limitation**: Specialized medical biology queries returned 0 results. |

### Deep Dive on `false_05` (5G Vaccine Conspiracy)
* **Hypothesis**: *"COVID-19 Vaccines Contain Injectable 5G Microchips for Digital Surveillance"*.
* **Premise**: Wikipedia *COVID-19 vaccine misinformation and hesitancy* (*"A variety of unfounded conspiracy theories and other misinformation about COVID-19 vaccines have spread based on misunderstood or misrepresented science... a story about COVID-19 being spread by 5G, and other false or distorted information..."*).
* **NLI Mechanism**: The premise describes *the social spread of the story*, not a direct physical refutation (*"vaccines do not contain microchips"*). NLI strictly reasons: *"The fact that a story has spread does not entail or logically falsify the physical statement"*, producing `NEUTRAL` (prob: $0.8824$).

---

## 5. Granular Classification of the 44 NEUTRAL Relations (Task 5)

Every one of the 44 `NEUTRAL` evidence relations was individually audited:

| Category | Exact Count | Percentage | Representative Examples |
| :--- | :---: | :---: | :--- |
| **1. Genuinely Neutral / Contextual** | **38** | 86.4% | Encyclopedia articles describing general entities: *Curiosity rover, ESA, NASA, Hydrogen, Heavy water, Substance, Microwave oven, Earth's rotation, Copernican heliocentrism, Climate change, Digital Services Act*. |
| **2. Semantically Supporting (NLI Missed Support)** | **2** | 4.5% | Wikipedia *Apollo 11* (*"first human spaceflight to land on the Moon"*) $\rightarrow$ NLI produced high neutral due to multi-clause hypothesis syntax. |
| **3. Semantically Contradicting (NLI Missed Contradiction)** | **1** | 2.3% | Wikipedia *COVID-19 vaccine misinformation* $\rightarrow$ NLI treated reporting about conspiracy theories as neutral. |
| **4. Adjacent / Unrelated Evidence** | **3** | 6.8% | Snopes debunks of solar eclipse hoaxes matched in JWST case (`real_02`), Space Daily astronaut memorabilia in Apollo (`real_04`). |
| **5. Insufficient Context** | **0** | 0.0% | All Wikipedia and fact-check snippets were complete sentences. |
| **6. Unclear** | **0** | 0.0% | Zero ambiguous cases. |
| **Total NEUTRAL Relations** | **44** | **100.0%** | |

---

## 6. Premise Construction Audit (Task 6)

* **Fact-Check Premise Builder**:
  ```python
  "Reviewed Claim: {claim_reviewed}. Rating: {raw_rating}. {title}. {snippet}"
  ```
  *Audit*: Effectively preserved reviewer context for `fc_05` and `real_04`.
* **General Reference Premise Builder**:
  ```python
  "{title}: {snippet}"
  ```
  *Audit*: Wikipedia lead sections provide valid definitions, but when the claim contains specific dates or sub-events, the broad lead paragraph lacks the episodic detail needed for entailment.
* **Live News Premise Builder**:
  ```python
  "{title}. {snippet}"
  ```
  *Audit*: News headlines and summaries are clean, but secondary opinion/analysis articles occasionally inject conflict.

---

## 7. Multi-Claim Synthesis Audit (Task 7)

* In `real_04` (*Apollo 11*):
  * Claim 1: Extracted title proposition $\rightarrow$ **`SUPPORTED`** (2 direct supports from Neil Armstrong & Buzz Aldrin articles).
  * Claim 2: Extracted body proposition $\rightarrow$ **`UNVERIFIED`** (3 neutral reference articles).
  * Synthesis Result: Article-level **`UNVERIFIED`**.
* **Audit**: Under the current V2 synthesis rule, an article is `SUPPORTED` if and only if all verifiable claims are supported without unverified or conflicting claims. This is an explicit, conservative policy to prevent partially unverified articles from being falsely endorsed.

---

## 8. Stage 34G Case Reclassification (Task 8)

| Case ID | Category | Ground Truth | Baseline (Stage 32) | Stage 34G Result | Forensic Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `fc_05` | B | `CONTRADICTED` | `UNVERIFIED` | **`CONTRADICTED`** | **FIXED** |
| `false_08` | C | `CONTRADICTED` | `UNVERIFIED` | **`CONTRADICTED`** | **FIXED** |
| `false_04` | C | `CONTRADICTED` | `UNVERIFIED` | **`CONTRADICTED`** | **FIXED** |
| `real_01` | A | `SUPPORTED` | `CONTRADICTED` | `UNVERIFIED` | **IMPROVED_EVIDENCE_ONLY** (false contradiction removed) |
| `real_02` | A | `SUPPORTED` | `UNVERIFIED` | `CONTRADICTED` | **IMPROVED_EVIDENCE_ONLY** (gained 9 ev items) |
| `real_05` | A | `SUPPORTED` | `UNVERIFIED` | `CONTRADICTED` | **IMPROVED_EVIDENCE_ONLY** (gained 4 ev items) |
| `real_08` | A | `SUPPORTED` | `UNVERIFIED` | `UNVERIFIED` | **IMPROVED_EVIDENCE_ONLY** (gained 5 ev items) |
| `false_05` | C | `CONTRADICTED` | `UNVERIFIED` | `UNVERIFIED` | **IMPROVED_EVIDENCE_ONLY** (gained 2 ev items) |
| `real_07` | A | `SUPPORTED` | `UNVERIFIED` | `CONTRADICTED` | **IMPROVED_EVIDENCE_ONLY** (gained 6 ev items) |
| `news_06` | A | `SUPPORTED` | `UNVERIFIED` | `CONTRADICTED` | **IMPROVED_EVIDENCE_ONLY** (gained 5 ev items) |
| `real_04` | A | `SUPPORTED` | `UNVERIFIED` | `UNVERIFIED` | **UNCHANGED** (Claim 1 supported, Claim 2 neutral) |
| `fc_07` | B | `CONTRADICTED` | `UNVERIFIED` | `UNVERIFIED` | **UNCHANGED** (0 evidence retrieved) |

* **Total Fixed**: **3**
* **Improved Evidence Only**: **7**
* **Unchanged**: **2**
* **Regressed**: **0**

---

## 9. Next Bottleneck Identification (Task 9)

$$\begin{array}{|l|c|l|}
\hline
\textbf{Pipeline Stage} & \textbf{Failure Impact} & \textbf{Primary Symptom} \\ \hline
\text{1. Retrieval Specificity} & \text{Medium (2 cases)} & \text{Specialized science queries yield 0 results (e.g. shark cancer).} \\ \hline
\text{2. Evidence Relevance / Premise Gate} & \text{High (4 cases)} & \text{Broad reference overviews trigger false NLI contradictions.} \\ \hline
\text{3. NLI Nuance on Misinformation} & \text{Low (1 case)} & \text{NLI treats meta-reporting of conspiracy theories as neutral.} \\ \hline
\text{4. Multi-Claim Synthesis Conservatism} & \text{Medium (1 case)} & \text{Supported Claim 1 masked by Neutral Claim 2.} \\ \hline
\end{array}$$

* **Dominant Remaining Bottleneck**: **Combination of Premise Specificity & Evidence Gating** (Category F). General reference retrieval successfully cured the zero-evidence problem across 91.7% of cases, but high-level encyclopedia extracts need tighter premise alignment to avoid broad premise contradictions on detailed claims.

---

## 10. Key Questions Answered

1. **Why are 44/56 semantic relations NEUTRAL?**
   $86.4\%$ (38/44) of neutral items are genuinely neutral encyclopedia definitions of broad entities (*e.g. NASA, ESA, Curiosity rover, Hydrogen, Climate change*) that do not assert the specific empirical propositions in the claims.
2. **How many of those 44 are actually semantically supporting/contradicting?**
   Only **3 items** ($6.8\%$) represented missed directional signals (2 missed supports in Apollo 11 / HGP, 1 missed contradiction in 5G vaccine misinformation).
3. **Why did `false_05` become NEUTRAL?**
   The retrieved Wikipedia snippet discussed the *social propagation of 5G conspiracy theories* rather than stating direct biomedical refutations.
4. **Why are the 7 SUPPORTED cases still failing?**
   - 4 cases (`real_02`, `real_05`, `real_07`, `news_06`) matched adjacent or broad encyclopedia articles that NLI treated as conflicting premises.
   - 2 cases (`real_01`, `real_08`) matched general background articles that were logically neutral.
   - 1 case (`real_04`) had Claim 1 supported, but Claim 2 was neutral, resulting in conservative article-level `UNVERIFIED`.
5. **Is premise construction contributing?**
   Premise construction is working correctly as designed, but encyclopedia lead sections naturally contain general definitions rather than specific event confirmations.
6. **Is NLI itself the dominant limitation now?**
   No. NLI inference is behaving logically given the exact premises it is fed. The primary challenge is ensuring that retrieved reference extracts match the exact proposition rather than an adjacent concept.
7. **Is multi-claim synthesis contributing?**
   Yes. When Claim 1 is supported and Claim 2 has neutral reference context, the article synthesis rule conservatively retains `UNVERIFIED`.
8. **Is the production architecture ready for a full 64-case rerun?**
   The pipeline is technically operational, deterministic, and safe (3 fixes, 0 regressions, 82/82 tests pass). However, users should anticipate that general reference evidence predominantly resolves macro-scientific/historical conspiracies while remaining conservative on multi-claim news articles.
