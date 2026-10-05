# Stage 42 — Fact-Check Proposition Matching Fix Report (Generalized Audit)

## 1. Executive Summary

In live UI verification of composite/cross-domain claims such as:
> *"5G towers spread coronavirus and cause COVID-19 infections."*

The Google Fact Check API previously returned generic or adjacent COVID-19 fact checks (e.g. *"COVID-19 does not spread from person to person"*, *"The coronavirus that causes COVID-19 is infectious"*). Because the system recognized the shared entity `"COVID-19"` and broad transmission verbs like `"spread"`, generic articles bypassed specificity gating. One adjacent fact-check was interpreted as `CONTRADICTS` while another was classified as `SUPPORTS`, inducing a false **CONFLICT → UNVERIFIED** outcome.

Stage 42 implements a **generalized proposition-alignment rule** in [`EvidenceMatcher`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/app/v2/evidence_matcher.py) that strictly enforces multi-core entity coverage and proposition predicate/object alignment for fact checks without any case-specific or hardcoded rules.

---

## 2. Root Cause Analysis

1. **Weak Entity Alignment Threshold for Multi-Entity Claims:**
   - In `_entities_match()`, `is_entity_aligned` was satisfied whenever `len(matched) > 0`.
   - When a claim paired distinct entities (e.g. a telecommunications entity and an infectious disease entity, or an agency and a policy), fact-checks reviewing one entity without mentioning the other were classified as `entity_aligned = True`.

2. **Generic Transmission / Linking Terms in Specific Proposition Overlap:**
   - Words like `"spread"`, `"transmit"`, `"cause"`, `"infect"`, and `"virus"` were counted in `specific_proposition_overlap`.
   - General articles that contained generic linking verbs satisfied `specific_proposition_overlap_count >= 1`, allowing them to pass as proposition-matched.

3. **Multi-Word Entity Overlap Inflation:**
   - Long multi-word entity names (e.g. `James Webb Space Telescope`, `Large Hadron Collider`) generated high raw token overlap counts, masking proposition object mismatch.

---

## 3. Generalized Proposition-Alignment Architecture

The final implementation eliminates all case-specific entity aliases (e.g. no hard-coded 5G tower/network permutations) and implements general algorithmic mechanisms:

### A. Generic Entity Extraction & Acronym Handling
- **Alphanumeric Codes & Acronyms:** Generic regular expressions (`\b[0-9]+[A-Za-z]+\b`, `\b[A-Za-z]+[0-9]+\b`, `\b[A-Za-z]+-[0-9]+\b`, `\b[A-Z]{2,}\b`) extract alphanumeric codes (`5G`, `6G`, `COVID-19`, `CRISPR`, `RFID`, `NASA`, `WHO`, `UNESCO`, `LHC`, `JWST`) automatically without explicit keyword enumeration.
- **Numbered Named Entities:** General pattern `\b[A-Z][a-z0-9'-]+\s*(?:-\s*)?\d+\b` extracts named mission and model entities (`Apollo 11`, `Falcon 9`, `Boeing 737`, `Voyager 1`) without hardcoding specific program names.
- **Acronym Casing Normalization:** Generic rule uppercasing single-token short words (`len(phrase) <= 6 and " " not in phrase`) and title-casing multi-word phrases.

### B. FrameNet / VerbNet Semantic Action Groups
- Semantic frames group semantically interchangeable predicates:
  - Discovery / Detection: `discover`, `find`, `detect`, `uncover`, `spot`
  - Motion / Landing: `land`, `touchdown`
  - Prohibition: `ban`, `prohibit`, `outlaw`, `restrict`
  - Authorization: `approve`, `authorize`, `clear`, `pass`
  - Announcement: `declare`, `announce`, `name`, `designate`
  - Causation / Propagation: `cause`, `spread`, `transmit`, `emit`, `induce`, `trigger`
  - Infection: `infect`, `contagious`

### C. Generic Proposition Term Subtraction
- Meta-discourse, reporting terms, and generic connecting verbs (`spread`, `transmit`, `cause`, `infect`, `disease`, `illness`, `virus`, `person`, `people`, `human`, `study`, `report`, `claim`, `wave`, `second`, etc.) are subtracted from `specific_proposition_overlap` so connecting relations cannot satisfy physical object overlap.

### D. Multi-Core Entity Alignment Rule for Fact Checks
- When a claim asserts a proposition across $\ge 2$ distinct core entities (e.g. Entity $E_1$ and Entity $E_2$):
  - A fact-check must contain all core entities or their standard recognized expansions.
  - If a core entity is absent in the reviewed claim and the match is not a specific numbered model/mission entity (`[A-Z][a-z0-9'-]+\s+\d+`, e.g. `Apollo 11`), the fact-check is deterministically classified as `IRRELEVANT`:
    $$\text{Relevance} = \text{IRRELEVANT}$$
    $$\text{Reason} = \text{"Rejected adjacent fact-check: Entity matched, but primary core entity was absent in reviewed claim."}$$

### E. Single-Entity Object Alignment Rule
- For single-entity claims (e.g. `JWST` or `Large Hadron Collider`), if the reviewed claim has $\ge 2$ missing proposition objects and zero specific proposition overlap with no debunk marker, it is rejected to prevent adjacent hoaxes from attaching.

---

## 4. Test Results & Verification

### Full Pytest Suite

```bash
PYTHONPATH=. pytest backend/app/v2/ backend/evaluation/test_*.py
```

**Result:**
- **118 passed, 0 failed, 2 warnings** (11.55s)

### Focused Test Suite (`backend/app/v2/test_fact_check_matching.py`)

| Test | Description | Result |
| :--- | :--- | :--- |
| **Test A** | User claim vs unrelated COVID fact-checks (missing 5G) | **REJECTED (IRRELEVANT)** |
| **Test B** | User claim vs directly aligned 5G fact-check | **ACCEPTED (RELEVANT, CONTRADICTS)** |
| **Test C** | Paraphrased aligned fact-checks (`"5G causes COVID-19"`, `"5G networks spread coronavirus"`) | **ACCEPTED (RELEVANT, CONTRADICTS)** |
| **Test D** | Generic topic overlap (COVID surfaces, vaccines) | **REJECTED (IRRELEVANT)** |
| **Test E** | Fact-check rating preserved when aligned (False $\rightarrow$ CONTRADICTS, True $\rightarrow$ SUPPORTS) | **PRESERVED** |
| **Test F** | Numbered entity (Apollo 11 vs Apollo 9) and temporal year (Tokyo 1923 vs 2024) regressions | **PASSED** |
| **Test G** | Deterministic evidence filtering and ordering consistency across repeated invocations | **PASSED** |

---

## 5. Multi-Domain Generalized Regression Results

### Test 1: 5G / COVID Proposition
- **Input Claim:** `"5G towers spread coronavirus and cause COVID-19 infections."`
- **Candidates:** 3 items (1 unrelated generic COVID spread, 1 aligned 5G spread, 1 paraphrased 5G causes COVID)
- **Accepted:** 2 items (aligned + paraphrased)
- **Rejected:** 1 item (`fc_unrelated_covid` rejected at gate)
- **Has Conflict:** `False`
- **Verdict:** `CONTRADICTED`

### Test 2: Arbitrary Domain Proposition (RFID / Vaccines)
- **Input Claim:** `"COVID-19 vaccines contain injectable RFID tracking microchips."`
- **Candidates:** 2 items (1 unrelated automotive microchip shortage, 1 aligned RFID vaccine fact-check)
- **Accepted:** 1 item (`fc_aligned_rfid`)
- **Rejected:** 1 item (`fc_unrelated_auto` rejected at gate)
- **Has Conflict:** `False`
- **Verdict:** `CONTRADICTED`

---

## 6. Frontend Build & Static Analysis

```bash
cd frontend && npm run lint && npm run build
```

**Result:**
- `oxlint`: 0 warnings, 0 errors across 7 files
- `vite build`: Built production bundle cleanly (dist/assets/index-BLZpNgF2.js 289.08 kB)

---

## 7. External Request Count

- **NewsAPI Requests:** 0
- **Google Fact Check API Requests:** 0
- **Wikipedia Requests:** 0
- **Total External Requests in Stage 42:** **0**
