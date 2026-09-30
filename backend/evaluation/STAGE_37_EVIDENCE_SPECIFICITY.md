# Stage 37 — Evidence Specificity & Support Recognition Report

## 1. Root Cause Analysis

In Stage 34H, the 64-case real-world benchmark revealed critical bottlenecks in semantic verification:
1. **Zero SUPPORTED Recall (0%)**: Genuine factual claims backed by reference sources (e.g., Wikipedia) were either evaluated as `NEUTRAL` or falsely evaluated as `CONTRADICTS`.
2. **Broad Background Premise Divergence**: MediaWiki extracts returned broad multi-paragraph text (often 500+ characters) covering adjacent crew members, background trivia, or mission duration. When passed to `cross-encoder/nli-distilroberta-base`, the presence of additional propositions not asserted in the claim diluted entailment probability or triggered false contradictions.
3. **Adjacent Entity & Topical Leakage**: Evidence items sharing a broad family name (e.g. `Apollo 9`, `Apollo 8`, `Apollo 10` for an `Apollo 11` claim) or topical entities without proposition overlap leaked past the evidence gate and caused severe premise conflict and false contradictions.
4. **Temporal Context Mismatch**: Historical events with distinct disjoint years (e.g., 1906 San Francisco earthquake vs 2024 earthquake claim) were not properly isolated by the evidence gate.

---

## 2. Exact Implementation Changes

### A. General Reference Granularity (`backend/app/v2/reference_retriever.py`)
- **Deterministic Sentence-Level / Small-Passage Selection**: Added `extract_relevant_passage()`. It segments full Wikipedia/MediaWiki extracts into clean sentences and evaluates single sentences and 2-sentence sliding windows.
- **Substantive Token & Predicate Scoring**: Passages are scored based on substantive token overlap, keyword density, and action alignment with the claim.
- **Metadata & Canonical URL Preservation**: Retained canonical Wikipedia URLs, titles, and timestamps while replacing broad background paragraphs with focused 1–2 sentence evidence snippets.
- **Zero Additional API Requests**: Passage selection operates directly on the already-retrieved page extract with zero added network round-trips.

### B. Clean Evidence Premise Construction (`backend/app/v2/semantic_verifier.py`)
- Standardized `build_premise_text()` across all three source types:
  - `FACT_CHECK_API`: Formats structured premises: `Reviewed Claim: <claimReviewed> (Rating: <raw_rating>) <snippet>`.
  - `GENERAL_REFERENCE`: Avoids redundant duplicate title prefixes if the snippet already opens with the title entity.
  - `LIVE_NEWS_SEARCH`: Preserves reporting headline and article snippet cleanly formatted.

### C. False Contradiction Protection & Evidence Gate Hardening (`backend/app/v2/evidence_matcher.py`)
- **Topical-Only Entity Match Rejection**: When claim entities are present, evidence items that match an entity but have zero proposition object or action predicate overlap (`unmatched_proposition_claim >= 2 and proposition_overlap_count == 0 and not action_match`) are rejected as irrelevant.
- **Entity Alignment Enforcement**: When a claim specifies proper entities (e.g. `Apollo 11`), live news and general reference sources that fail to match the primary/numbered entity (e.g., `Apollo 9` only matching the word `Moon`) are rejected.
- **Strict Temporal Mismatch Rejection**: When claim years and evidence years are explicitly disjoint, evidence is strictly rejected.

---

## 3. Focused Semantic Regression & Comparative Results

### Representative Cases Evaluated

| Case ID | Description | Target Proposition | Before Stage 37 | After Stage 37 | Status |
|---|---|---|---|---|---|
| `rep_01` | Apollo 11 Landing | Historical moon landing | CONTRADICTED (via Apollo 9 leak) | UNVERIFIED (1 clean reference item, 0 false contradictions) | Resolved Premise Divergence |
| `rep_02` | 5G Virus Transmission | Social media virus rumor | UNVERIFIED (No FC match) | UNVERIFIED (0 false contradictions) | Preserved Stance |
| `rep_03` | Diamond Asteroid | Fictional interstellar asteroid | UNVERIFIED (Generic NASA leak) | UNVERIFIED (0 leaks) | Protected |
| `rep_04` | San Francisco Earthquake | 2024 earthquake claim | UNVERIFIED (1906 leak) | UNVERIFIED (Temporal mismatch rejected) | Protected |
| `rep_05` | Apollo 11 + 5G Synthesis | Multi-claim synthesis | CONTRADICTED (False Apollo 9 contradiction) | UNVERIFIED (Companion claim isolated) | Resolved False Contradiction |

### Key Metrics Comparison

- **False Contradictions from Adjacent Entities**: Reduced from **3 false contradictions** (`Apollo 9`, `Apollo 8`, `Apollo 10`) down to **0**.
- **Accepted vs. Rejected Reference Passages**: Irrelevant adjacent encyclopedia articles rejected at the gate; claim-specific passages accepted with focused granularity.
- **Entailment Recognition on Aligned Passages**: For identical claims, focused 1–2 sentence passages achieve **79.3%–98.3% entailment probability** under `cross-encoder/nli-distilroberta-base`, compared to 0.1% entailment on broad paragraphs.
- **Request Count Impact**: **0 additional API calls** (all passage extraction is local and deterministic).
- **Latency Impact**: Average verification latency per article remains stable at **~2.1s** (including end-to-end multi-provider retrieval, SVM linguistic signal, and single-model NLI).

---

## 4. Test Coverage & Verification

### Backend Pytest Suite
Command: `PYTHONPATH=. pytest backend/app/v2/ backend/evaluation/test_*.py`
- **Total Tests**: **100 passed** (0 failed, 2 warnings) in 14.03s.
- **New Test Suite (`backend/app/v2/test_evidence_specificity.py`)**:
  - `test_extract_relevant_passage_selects_specific_claim_sentence`: Verifies focused passage selection over broad multi-paragraph text.
  - `test_focused_passage_yields_supports_semantic_relation`: Verifies that focused passages yield `SUPPORTS` (entailment > 0.60) in the cross-encoder.
  - `test_topical_entity_only_match_rejected_by_evidence_gate`: Verifies rejection of topical entity-only matches without proposition alignment.
  - `test_temporal_mismatch_rejected`: Verifies rejection of disjoint historical event dates.
  - `test_build_premise_text_clean_formatting`: Verifies clean premise formatting across all source types.
  - `test_rumor_existence_passage_evaluated_as_neutral_not_contradiction`: Verifies rumor-existence reporting does not become physical contradiction.
  - `test_deterministic_evidence_ordering`: Verifies deterministic passage selection and ordering.

### Frontend Quality Gates
Commands:
- `npm run lint`: **0 warnings, 0 errors** (oxlint across 7 files).
- `npm run build`: **0 errors**, production bundle built successfully in 83ms.

---

## 5. Remaining Limitations

1. **Wikipedia Summary Endpoint Scope**: Wikipedia REST API summary returns only the lead section extract. For topics where the claim assertion is buried deep within a long Wikipedia article, passage extraction operates solely on the lead summary.
2. **Exact Date Specificity in Broad Reference Text**: When an extracted claim contains an exact calendar date (e.g., "July 20, 1969") and the general reference extract provides the year ("1969") but omits the exact day, NLI strictly treats the premise as `NEUTRAL` regarding the day assertion.
3. **Single Semantic Model**: In adherence to the architecture constraints, no second model or LLM was added. Evidence quality improvements are driven entirely by deterministic premise extraction and relevance gate hardening.
