# Stage 33D — Evidence Suitability Audit for Semantic Verification

## 1. Executive Summary

This audit evaluates whether the evidence retrieved by the V2 verification pipeline across the 64-case benchmark and Stage 33C targeted regression is sufficiently informative and semantically aligned for an upstream or single semantic claim-verification model.

### Key Audit Findings:
* **Total Benchmark Cases:** 64
* **Cases with Retrieved Evidence:** **16 / 64 (25.00%)** (38 total evidence items)
* **Cases with Zero Retrieved Evidence:** **48 / 64 (75.00%)**
* **Cases with Direct Exact Evidence (Usable for Semantic Verification):** **7 / 64 (10.94%)**
  - All 7 are Ground-Truth `CONTRADICTED` cases where Google Fact Check Tools returned explicit debunk articles.
* **Ground-Truth `SUPPORTED` Cases Usable:** **0 / 16 (0.00%)**
  - 11 cases yielded 0 evidence.
  - 3 cases matched adjacent hoax debunks on true entities (`real_01`, `real_03`, `real_04`).
  - 2 cases returned neutral news reporting lacking explicit verification (`real_06`, `real_08`).
* **Ground-Truth `CONTRADICTED` Cases Usable:** **7 / 23 (30.43%)**
  - 7 cases contain direct fact-check debunks.
  - 16 cases yielded 0 evidence (synthetic hoaxes / niche falsehoods not indexed by Google Fact Check Tools).
* **Adjacent Hoax Debunk Risk:** When evidence *is* retrieved for true entities, **6 of 16 evidence-bearing cases (37.50%)** retrieved debunks of adjacent conspiracies/hoaxes rather than establishing the actual proposition.

---

## 2. Actual Available Evidence Context Fields (Task 1)

Inspecting the preserved raw evaluation records (`real_world_results_combined.json`, `real_world_results_batch_1.json`, `real_world_results_batch_2.json`, `real_world_results_retrieval_regression.json`) and the V2 schemas reveals the following concrete fields:

| Field Name | Type | Availability in FC | Availability in NewsAPI | Content Description & Utility |
| :--- | :--- | :---: | :---: | :--- |
| `title` | `str` | 100% | 100% | Headline or claim review title (e.g. *"Fact check: Moon landing conspiracy theory..."*). |
| `snippet` / `description` | `str` | 100% | 100% | FC: `"Reviewed Claim: '...' \| Rating: ..."`<br>NewsAPI: Article summary text + source name. |
| `claim_reviewed` | `Optional[str]` | 100% | 0% (`None`) | The exact verbatim proposition evaluated by the fact-checker. Highly informative for NLI. |
| `raw_rating` | `Optional[str]` | 100% | 0% (`None`) | Raw textual rating string (e.g., `"False"`, `"Pants on Fire"`, `"True"`, `"Miscaptioned"`). |
| `publisher` | `str` | 100% | 100% | Authoritative publisher name (e.g. `Snopes`, `Reuters`, `PolitiFact`, `Full Fact`, `AFP`). |
| `domain` | `str` | 100% | 100% | Cleaned domain hostname (e.g. `snopes.com`, `fullfact.org`, `reuters.com`). |
| `url` | `str` | 100% | 100% | Canonical review or news article URL (secrets redacted). |
| `publish_date` | `Optional[str]` | ~95% | 100% | ISO 8601 publication or review timestamp. |
| `source_type` | `Enum` | 100% | 100% | Disambiguates `FACT_CHECK_API` vs `LIVE_NEWS_SEARCH`. |
| `stance` | `Enum` | 100% | 100% | Rule-mapped stance (`SUPPORTS`, `CONTRADICTS`, `NEUTRAL`). |
| `relevance_score` | `Optional[float]` | 100% | 100% | Lexical token overlap ratio produced by `EvidenceMatcher`. |

---

## 3. Evidence Suitability Taxonomy & Benchmark Distribution (Task 2)

All 64 benchmark cases are classified into 4 mutually exclusive suitability categories:

```
+-------------------------------------------------------------------------------+
|                    64 BENCHMARK CASES EVIDENCE SUITABILITY                    |
+-------------------------------------------------------------------------------+
|  Category A: Direct Exact Match           |  7 cases (10.94%)                 |
|  Category B: Semantic Related Context     |  3 cases ( 4.69%)                 |
|  Category C: Adjacent Hoax Debunk         |  6 cases ( 9.38%)                 |
|  Category E: Zero Usable Evidence         | 48 cases (75.00%)                 |
+-------------------------------------------------------------------------------+
```

### Breakdown of Categories:

1. **Category A — Direct Exact Match (7 cases / 10.94%):**
   * Cases: `false_01` (Pope Puffer), `false_02` (15 Days Darkness), `false_03` (Lemon Water Cancer), `false_06` (Great Wall from Moon), `fc_01` (5G Radiation), `fc_04` (UNESCO Anthem), `fc_05` (Microwave Food Toxic).
   * *Suitability:* **Usable for semantic verification.** Published fact-checkers reviewed the exact proposition, providing clear textual premise-hypothesis pairs.

2. **Category B — Semantically Related News Context (3 cases / 4.69%):**
   * Cases: `real_06` (CERN Higgs), `real_08` (CRISPR Nobel), `multi_08` (SpaceX Starship).
   * *Suitability:* **Insufficient on its own.** Live news articles mention the entities and broad domain context (e.g. LHC upgrades or cryogenic propellant tests), but do not explicitly affirm or refute the historical milestone proposition.

3. **Category C — Adjacent Hoax Debunks Applied to True Claims (6 cases / 9.38%):**
   * Cases: `real_01` (Mars Organics), `real_03` (WHO COVID), `real_04` (Apollo 11), `multi_03` (Apollo+JWST), `multi_05` (WHO COVID), `multi_06` (CERN Higgs).
   * *Suitability:* **High risk of false contradiction.** Google Fact Check returned debunks of viral conspiracies (e.g. *Buzz Aldrin boot print hoax*, *NASA life on Mars hoax*, *Steve Barclay premature COVID declaration*). Keyword overlap matches the entity, but the premise refutes an adjacent falsehood rather than supporting the true claim.

4. **Category E — Zero Usable Evidence Retrieved (48 cases / 75.00%):**
   * Cases: 11 `SUPPORTED`, 16 `CONTRADICTED`, 21 `UNVERIFIED`.
   * *Suitability:* **Cannot be verified semantically.** No external text premise exists to pass into a verification model.

---

## 4. Ground-Truth `SUPPORTED` Case Analysis (Task 3)

Across the 16 ground-truth `SUPPORTED` cases:

| Metric | Count | % of SUPPORTED | Explanation |
| :--- | :---: | :---: | :--- |
| **Direct Usable Evidence** | **0** | **0.00%** | Not a single ground-truth supported case has direct, unambiguous supporting fact-check evidence. |
| **Adjacent Hoax Debunks** | **3** | **18.75%** | `real_01`, `real_03`, `real_04` matched adjacent conspiracy debunks. |
| **Neutral News Context Only** | **2** | **12.50%** | `real_06` (Gizmodo on LHC), `real_08` (PLOS on DNA). |
| **Zero Evidence Retrieved** | **11** | **68.75%** | `real_05`, `real_07`, `news_01`–`news_08`. |

### Conclusion on SUPPORTED Cases:
Fact-checking search APIs (Google Fact Check Tools) almost exclusively index *refutations of falsehoods*. Established scientific and historical facts (e.g., *Apollo 11 landed in 1969*, *Water is H2O*, *WHO declared end of PHEIC*) rarely exist as positive `"True"` fact-check reviews. Without authoritative general web/encyclopedic retrieval, a semantic verification model will receive 0 evidence for ~69% of true claims and misleading adjacent debunks for ~19%.

---

## 5. Ground-Truth `CONTRADICTED` Case Analysis (Task 4)

Across the 23 ground-truth `CONTRADICTED` cases:

| Metric | Count | % of CONTRADICTED | Explanation |
| :--- | :---: | :---: | :--- |
| **Direct Usable Debunk Evidence** | **7** | **30.43%** | `false_01`, `false_02`, `false_03`, `false_06`, `fc_01`, `fc_04`, `fc_05` contain explicit debunk reviews. |
| **Indirect / Adjacent Debunk Evidence** | **0** | **0.00%** | None of the false claims received adjacent debunks. |
| **Zero Evidence Retrieved** | **16** | **69.57%** | `false_04`, `false_05`, `false_07`, `false_08`, `fc_02`, `fc_03`, `fc_06`, `fc_07`, `fc_08`, `synth_01`–`synth_08`. |

### Conclusion on CONTRADICTED Cases:
When a false claim is a widely publicized viral hoax (e.g. *Pope puffer coat*, *lemon water cancer*, *5G COVID*), Google Fact Check delivers high-quality premise text. However, 69.57% of false cases in the benchmark (including synthetic claims and niche hoaxes) are not indexed in Fact Check Tools, resulting in zero evidence.

---

## 6. Stage 33C Targeted Regression Analysis (Task 5)

In Stage 33C, the improved query builder (scaffolding removal, salience ranking, canonical alias expansion) was evaluated against all 27 retrieval failure cases:

* **Cases evaluated:** 27
* **Cases remaining at 0 evidence:** **26 / 27 (96.30%)**
* **Cases with newly retrieved evidence:** **1 / 27 (3.70%)** (`real_02`: James Webb Deepest Infrared Image)
* **Analysis of `real_02` Evidence:**
  - Google Fact Check returned 3 Snopes articles on JWST (*"Cosmic Vine image hoax"* and *"2024 Solar Eclipse photo hoax"*).
  - Both articles debunked viral fakes related to JWST images.
  - Because Snopes rated the hoax as `"False"`, the downstream matcher classified it as `CONTRADICTS`, flipping `real_02` from `UNVERIFIED` to `CONTRADICTED`.
* **Implication:** Broadening entity query recall without semantic premise-hypothesis entailment reasoning exacerbates the adjacent-claim vulnerability.

---

## 7. Recommended Model Input Contract (Task 6)

Based strictly on the available evidence fields, a single semantic verification / NLI model should consume the following structured input representation:

```python
class SemanticVerificationInput(BaseModel):
    # Claim to verify (Hypothesis)
    claim_id: str
    claim_text: str
    
    # Retrieved Evidence Context (Premise)
    evidence_id: str
    source_type: str                  # "FACT_CHECK_API" | "LIVE_NEWS_SEARCH"
    publisher: str                    # e.g., "Snopes", "Reuters", "PolitiFact"
    domain: str                       # e.g., "snopes.com", "fullfact.org"
    evidence_title: str               # Headline
    evidence_snippet: str             # Full text snippet / description
    claim_reviewed: Optional[str]     # Exact proposition reviewed by fact-checker
    raw_rating: Optional[str]         # e.g., "False", "True", "Miscaptioned"
    
    # Combined Premise Text for NLI Tokenization:
    # If Fact Check: "Reviewed Claim: {claim_reviewed or evidence_title}. Publisher Rating: {raw_rating}."
    # If Live News:  "{evidence_title}. {evidence_snippet}"
```

---

## 8. Fundamental Limitation & Next Steps (Task 7)

### Core Diagnosis:
1. **Primary Upstream Bottleneck — Retrieval Availability (75.00% of benchmark):**
   - 48 of 64 cases have **zero external evidence** returned by Google Fact Check Tools and NewsAPI.
   - Fact Check Tools only indexes debunked viral hoaxes; NewsAPI `/v2/everything` only indexes live rolling news within a 30-day window.
   - Neither provider indexes general encyclopedic knowledge, scientific literature, or historical consensus facts.
2. **Secondary Downstream Bottleneck — Lack of Textual Entailment Reasoning (37.50% of evidence-bearing cases):**
   - For the 16 cases with retrieved evidence, rule-based keyword matching cannot distinguish between:
     - A fact-check debunking the *user's claim* (e.g. *Lemon water cures cancer* $\rightarrow$ False $\Rightarrow$ `CONTRADICTS`), versus
     - A fact-check debunking a *hoax denying the true claim* (e.g. *Apollo 11 was faked* $\rightarrow$ False $\Rightarrow$ `SUPPORTS` the landing).
3. **Sequential Priority:**
   - A semantic NLI model will resolve the downstream adjacent-claim mismatch (improving accuracy on the 16 evidence-bearing cases), but cannot resolve the 48 cases where retrieval returns zero evidence.

---

## 9. Complete 64-Case Case-by-Case Evidence Audit Table

| Case ID | Category | Ground Truth | Stage 32 Pred | Ev Count | Suitability Classification | Usable for NLI? | Primary Limitation |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: | :--- |
| `real_01` | Known True | SUPPORTED | CONTRADICTED | 1 | ADJACENT_HOAX_DEBUNK | No | ADJACENT_CLAIM_MISMATCH |
| `real_02` | Known True | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `real_03` | Known True | SUPPORTED | CONTRADICTED | 2 | ADJACENT_HOAX_DEBUNK | No | ADJACENT_CLAIM_MISMATCH |
| `real_04` | Known True | SUPPORTED | UNVERIFIED | 10 | ADJACENT_HOAX_DEBUNK | No | ADJACENT_CLAIM_MISMATCH |
| `real_05` | Known True | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `real_06` | Known True | SUPPORTED | UNVERIFIED | 1 | SEMANTIC_RELATED_CONTEXT | No | INSUFFICIENT_PROPOSITION_CONTEXT |
| `real_07` | Known True | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `real_08` | Known True | SUPPORTED | UNVERIFIED | 1 | SEMANTIC_RELATED_CONTEXT | No | INSUFFICIENT_PROPOSITION_CONTEXT |
| `false_01` | Known False | CONTRADICTED | CONTRADICTED | 3 | DIRECT_EXACT_MATCH | **Yes** | NONE |
| `false_02` | Known False | CONTRADICTED | CONTRADICTED | 1 | DIRECT_EXACT_MATCH | **Yes** | NONE |
| `false_03` | Known False | CONTRADICTED | CONTRADICTED | 3 | DIRECT_EXACT_MATCH | **Yes** | NONE |
| `false_04` | Known False | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `false_05` | Known False | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `false_06` | Known False | CONTRADICTED | CONTRADICTED | 1 | DIRECT_EXACT_MATCH | **Yes** | NONE |
| `false_07` | Known False | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `false_08` | Known False | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `unver_01` | Unverified | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `unver_02` | Unverified | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `unver_03` | Unverified | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `unver_04` | Unverified | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `unver_05` | Unverified | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `unver_06` | Unverified | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `unver_07` | Unverified | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `unver_08` | Unverified | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `fc_01` | Published FC | CONTRADICTED | CONTRADICTED | 1 | DIRECT_EXACT_MATCH | **Yes** | NONE |
| `fc_02` | Published FC | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `fc_03` | Published FC | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `fc_04` | Published FC | CONTRADICTED | CONTRADICTED | 2 | DIRECT_EXACT_MATCH | **Yes** | NONE |
| `fc_05` | Published FC | CONTRADICTED | UNVERIFIED | 1 | DIRECT_EXACT_MATCH | **Yes** | STANCE_POLARITY_MAPPING |
| `fc_06` | Published FC | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `fc_07` | Published FC | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `fc_08` | Published FC | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_01` | Breaking News | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_02` | Breaking News | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_03` | Breaking News | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_04` | Breaking News | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_05` | Breaking News | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_06` | Breaking News | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_07` | Breaking News | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_08` | Breaking News | SUPPORTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_unver_01` | Breaking News | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_unver_02` | Breaking News | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_unver_03` | Breaking News | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_unver_04` | Breaking News | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_unver_05` | Breaking News | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_unver_06` | Breaking News | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_unver_07` | Breaking News | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `news_unver_08` | Breaking News | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `synth_01` | Synthetic | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `synth_02` | Synthetic | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `synth_03` | Synthetic | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `synth_04` | Synthetic | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `synth_05` | Synthetic | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `synth_06` | Synthetic | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `synth_07` | Synthetic | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `synth_08` | Synthetic | CONTRADICTED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `multi_01` | Multi-Claim | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `multi_02` | Multi-Claim | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `multi_03` | Multi-Claim | UNVERIFIED | UNVERIFIED | 3 | ADJACENT_HOAX_DEBUNK | No | ADJACENT_CLAIM_MISMATCH |
| `multi_04` | Multi-Claim | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `multi_05` | Multi-Claim | UNVERIFIED | UNVERIFIED | 2 | ADJACENT_HOAX_DEBUNK | No | ADJACENT_CLAIM_MISMATCH |
| `multi_06` | Multi-Claim | UNVERIFIED | CONTRADICTED | 1 | ADJACENT_HOAX_DEBUNK | No | ADJACENT_CLAIM_MISMATCH |
| `multi_07` | Multi-Claim | UNVERIFIED | UNVERIFIED | 0 | ZERO_USABLE_EVIDENCE | No | RETRIEVAL_UNAVAILABLE |
| `multi_08` | Multi-Claim | UNVERIFIED | CONTRADICTED | 5 | SEMANTIC_RELATED_CONTEXT | No | INSUFFICIENT_PROPOSITION_CONTEXT |
