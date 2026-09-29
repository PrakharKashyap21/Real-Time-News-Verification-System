# Stage 34E — Evidence Gate Refinement for Semantic Verification

## 1. Executive Summary

Stage 34E refines the boundary between deterministic evidence filtering (`EvidenceMatcher`) and semantic entailment verification (`cross-encoder/nli-distilroberta-base`). The goal is to ensure legitimate proposition-level evidence is not rejected prematurely due to superficial lexical mismatches, while preventing adjacent hoaxes, temporal mismatches, and unrelated claims from reaching the NLI verifier.

### Core Principles Maintained
- **Deterministic Gate Role**: Answers *"Is this evidence plausibly about the same claim proposition?"* (relevance gating).
- **Semantic Verifier Role**: Answers *"Does this candidate evidence support, contradict, or remain neutral toward the claim?"* (stance classification).
- **Zero Production Verdict Impact**: No modifications were made to production `VerdictEngine` or final verdict decision thresholds.
- **Zero External API Calls**: All evaluations and regression tests ran strictly offline on preserved local artifacts and unit mocks.
- **Safety**: No arbitrary global lowering of lexical thresholds; refined category rules with deterministic safeguards for entities, predicates, proposition objects, and dates.

---

## 2. Root Cause Diagnoses (Task 1)

### 1. `real_05` (Water Molecule Composition) — Premature Rejection
- **Claim**: *"Water molecule chemical composition consists of hydrogen and oxygen"*
- **Evidence Item**: Wikipedia page `"Molecule"`, with extract: *"Water is a chemical compound consisting of two hydrogen atoms and one oxygen atom (H2O)."*
- **Root Cause**: `EvidenceMatcher._get_target_text()` previously evaluated `item.title or item.snippet` in general reference mode, using only the title (`"Molecule"`) and discarding the snippet extract. Furthermore, substantive lexical matching did not properly handle reference text pairing.
- **Fix**: Updated `_get_target_text()` to evaluate `f"{item.title} {item.snippet}"` for non-fact-check items. General reference matches evaluate entities (`Hydrogen`, `Oxygen`) and proposition terms against the full extract text.

### 2. `real_02` (JWST Adjacent Hoax) — False Contradiction Admission
- **Claim**: *"James Webb Space Telescope unveils deepest infrared image of early universe"*
- **Evidence Item**: Fact check reviewing a viral hoax: *"Photo shows a slice of chorizo sausage, not a star from James Webb Space Telescope"*.
- **Root Cause**: The entity name `"James Webb Space Telescope"` contains 4 words. Matching the entity name alone yielded a token overlap ratio of $4/8 = 0.50$, satisfying the generic overlap gate despite zero proposition overlap (`deepest, infrared, universe` vs `slice, chorizo, sausage, star`). The NLI verifier then saw the debunk text and classified it as `CONTRADICTS`.
- **Fix**: Refined proposition extraction to evaluate non-entity proposition objects (`unmatched_proposition_claim`). When a fact-check reviews an adjacent topic with zero proposition object overlap (`len(unmatched_proposition_claim) >= 2 and proposition_overlap_count == 0`), it is rejected deterministically as `IRRELEVANT`.

### 3. `real_01` (Voyager 2012 vs 2024) — Temporal Event Mismatch
- **Claim**: *"NASA Voyager 1 reached interstellar space in August 2012"*
- **Evidence Item**: News/reference article about Voyager 1 communication glitch occurring in **2024**.
- **Root Cause**: The matcher extracted entities (`Voyager 1`) and dates but lacked a deterministic year-mismatch rejection rule when concrete distinct 4-digit years were present with disjoint actions and zero proposition overlap.
- **Fix**: Added explicit temporal guardrail: When both claim and candidate evidence contain explicit 4-digit years that are completely disjoint (`claim_years.isdisjoint(target_years)`), have no action predicate match, and have zero proposition overlap, the candidate is classified as `IRRELEVANT`.

---

## 3. Evidence Gate Refinements (Tasks 2, 3, 4)

### A. Substantive Proposition & Object Extraction
The matcher decomposes claims into:
1. **Named Entities & Aliases**: (e.g. `James Webb Space Telescope`, `Apollo 11`, `COVID-19`).
2. **Action Predicates**: Mapped through semantic verb synonym groups (e.g. `{"land", "landed", "landing"}`, `{"discover", "detected"}`, `{"ban", "banned"}`).
3. **Core Proposition Objects**: Substantive non-stopword tokens excluding matched entities and matched action verbs (`unmatched_proposition_claim`).

### B. Fact-Check Matching Safeguards (`claimReviewed`)
For fact-check evidence:
- **Prioritize `claimReviewed`**: Matches specifically against the reviewed assertion rather than the debunker's editorial title.
- **Adjacent Debunk Rejection**: If $\ge 2$ core proposition objects in the claim are completely absent from the reviewed claim (`proposition_overlap_count == 0`), the item is rejected.
- **Debunk Refutation of Hoaxes**: Direct debunks of denials (e.g., *"Apollo 11 moon landing was staged: Rating False"*) are recognized as confirming historical claims when action and entities align.

### C. Temporal Event Guardrails
- Distinguishes same-entity distinct-event candidates (e.g. Voyager 2012 interstellar entry vs Voyager 2024 telemetry glitch).
- Rejects candidate items with disjoint 4-digit years when action predicates and proposition objects do not match.

---

## 4. 8-Case Local Evaluation: Before vs. After (Task 7)

| Case ID | Claim Archetype | Stage 34D Gate | Stage 34D NLI | Stage 34E Gate | Stage 34E NLI | Stage 34E Stance Summary |
|---|---|---|---|---|---|---|
| `real_02` | JWST Deepest Infrared Image (Adjacent Hoax) | ACCEPTED | CONTRADICTS (0.884) | **REJECTED (IRRELEVANT)** | Not Invoked | **NO_ACCEPTED_EVIDENCE** (Protected) |
| `real_04` | Apollo 11 Moon Landing 1969 (Debunk Hoax) | ACCEPTED | SUPPORTS (0.948) | **ACCEPTED (RELEVANT)** | SUPPORTS (0.948) | **ALL_SUPPORTS** |
| `real_08` | CRISPR Development (Adjacent Vaccine Hoax) | REJECTED | Not Invoked | **REJECTED (IRRELEVANT)** | Not Invoked | **NO_ACCEPTED_EVIDENCE** (Protected) |
| `real_01` | Voyager Interstellar Space (2012 vs 2024) | ACCEPTED | CONTRADICTS (0.757) | **REJECTED (IRRELEVANT)** | Not Invoked | **NO_ACCEPTED_EVIDENCE** (Protected) |
| `fc_05` | EU Combustion Engine Ban 2035 | ACCEPTED | SUPPORTS (0.953) | **ACCEPTED (RELEVANT)** | SUPPORTS (0.953) | **ALL_SUPPORTS** |
| `real_05` | Water Molecule Chemical Composition | REJECTED | Not Invoked | **ACCEPTED (RELEVANT)** | SUPPORTS (0.545) | **ALL_SUPPORTS** (Recovered) |
| `real_07` | Paris Climate Agreement Adoption | ACCEPTED | SUPPORTS (0.984) | **ACCEPTED (RELEVANT)** | SUPPORTS (0.984) | **ALL_SUPPORTS** |
| `false_05` | COVID 5G Microchips Conspiracy | ACCEPTED | CONTRADICTS (0.793) | **ACCEPTED (RELEVANT)** | CONTRADICTS (0.793) | **ALL_CONTRADICTS** |

---

## 5. Summary of Achievements

1. **Valid Evidence Recovery**:
   - `real_05` (Water chemical composition from Wikipedia) successfully passes the relevance gate and is verified by NLI as `SUPPORTS` (entailment probability 0.545).
2. **Adjacent-Hoax Protection**:
   - `real_02` (JWST chorizo sausage hoax) is rejected at the gate (`IRRELEVANT`), preventing false contradiction.
   - `real_08` (CRISPR COVID vaccine hoax) remains rejected at the gate (`IRRELEVANT`), preventing false contradiction.
3. **Temporal Mismatch Protection**:
   - `real_01` (Voyager 2012 vs 2024 telemetry glitch) is rejected at the gate (`IRRELEVANT`), preventing false contradiction.
4. **Preserved True Verifications**:
   - `real_04` (Apollo 11), `fc_05` (EU cars ban), `real_07` (Paris Agreement), and `false_05` (5G microchip debunk) continue to pass the gate with correct semantic stances.

---

## 6. Safety Audit (Task 8)

- **No Global Threshold Relaxation**: Thresholds were not lowered indiscriminately; instead, structural checks on proposition terms, action groups, and temporal markers were introduced.
- **No Production VerdictEngine Changes**: All changes remain strictly inside `evidence_matcher.py` relevance rules and evaluation prototypes.
- **No Additional ML Models**: Exactly one semantic model (`cross-encoder/nli-distilroberta-base`) is used.
- **No External API Calls**: Verified offline via deterministic unit and regression tests.
- **No Benchmark Modifications**: Dataset files and ground truth labels remain completely untouched.

---

## 7. Test Suite Status (Task 10)

- **Total Tests**: 68 passed, 0 failed.
- **Suite Command**: `PYTHONPATH=. pytest backend/app/v2/ backend/evaluation/ -v`
- **Execution Time**: ~16s
