# Stage 34A — General Reference Evidence Feasibility Report

## 1. Executive Summary

This feasibility experiment evaluates whether a **general reference / encyclopedic source** (tested via the public, unauthenticated MediaWiki / Wikipedia API) can recover informative and semantically aligned evidence for claims that currently receive zero usable evidence from Google Fact Check Tools and NewsAPI.

### Key Feasibility Findings:
* **Test Dataset:** Exactly 12 representative benchmark cases classified as `ZERO_USABLE_EVIDENCE` in Stage 33D across historical, scientific, institutional, physical, and synthetic categories.
* **API Reachability:** 100% reachable with zero authentication required. Mean response latency: **2,423.96 ms** for multi-stage search and summary retrieval.
* **Evidence Recovery Rate:** **11 / 12 cases (91.67%)** retrieved candidate pages.
* **Directly Relevant Evidence:** **8 / 12 cases (66.67%)** retrieved direct, proposition-level factual premises suitable for a semantic verifier.
* **Related Contextual Evidence:** **1 / 12 cases (8.33%)** (`false_07`).
* **Unrelated / Off-Topic Pages:** **2 / 12 cases (16.67%)** (`synth_01`, `unver_07`).
* **Zero Pages Found:** **1 / 12 cases (8.33%)** (`fc_06`).
* **Core Takeaway:** Integrating a general reference source provides strong coverage for scientific consensus facts, major historical milestones, established public legislation, and widespread scientific/historical misconceptions, directly solving the zero-evidence blindspot for non-debunk claims.

---

## 2. Selection of the 12 Zero-Evidence Test Cases (Task 1)

The 12 test cases were selected from `evidence_suitability_audit.json` to cover diverse claim archetypes:

| Case ID | Category | Ground Truth | Claim Proposition | Archetype |
| :--- | :--- | :---: | :--- | :--- |
| `real_02` | Known True | SUPPORTED | *James Webb Space Telescope Unveils Deepest Infrared Image of Universe* | Astronomical / Milestone |
| `real_05` | Known True | SUPPORTED | *Water Molecule Chemical Composition Consists of Hydrogen and Oxygen* | Chemical Consensus Fact |
| `real_07` | Known True | SUPPORTED | *Paris Agreement on Climate Change Adopted by International Consensus* | Environmental / Treaty |
| `false_04` | Known False | CONTRADICTED | *Earth Is Flat Disk and NASA Edits All Satellite Photographs* | Anti-Scientific Hoax |
| `false_05` | Known False | CONTRADICTED | *COVID-19 Vaccines Contain Injectable 5G Microchips for Digital Surveillance* | Viral Conspiracy Myth |
| `false_07` | Known False | CONTRADICTED | *Drinking Household Chemical Disinfectant Safely Cleans Viral Pathogens* | Hazardous Ingestion Hoax |
| `false_08` | Known False | CONTRADICTED | *Sun Revolves Around Stationary Earth Every 24 Hours* | Geocentric Astronomy Myth |
| `fc_06` | Published FC | CONTRADICTED | *Eating Carrots Gives Humans Night Vision and Cures Myopia* | Physiological Myth |
| `fc_07` | Published FC | CONTRADICTED | *Sharks Do Not Suffer from Cancer and Shark Cartilage Cures Malignant Tumors* | Oncology Misconception |
| `news_06` | Breaking News | SUPPORTED | *European Parliament Passed EU Artificial Intelligence Act* | Institutional / Legislation |
| `synth_01` | Synthetic | CONTRADICTED | *European Union Passes Emergency Law Mandating RFID Microchip Implants* | Synthetic Institutional Hoax |
| `unver_07` | Unverified | UNVERIFIED | *Coin Collector Claims Finding 1923 Silver Dollar Hand-Signed by President Coolidge* | Niche Unverified Claim |

---

## 3. MediaWiki / Wikipedia API Reachability & Protocol (Task 2)

* **Endpoints Tested:**
  1. Action API: `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srlimit=3`
  2. REST Summary API: `https://en.wikipedia.org/api/rest_v1/page/summary/{title}`
* **Authentication:** None required (unauthenticated public API with descriptive `User-Agent` header).
* **HTTP Availability:** 100% (12/12 cases succeeded with HTTP 200).
* **Latency Profile:**
  - Fast single-endpoint search: ~800–1,000 ms.
  - Multi-candidate fetch (1 search + 3 summary extracts): **Mean 2,423.96 ms**.
* **Rate Limits:** No HTTP 429 errors encountered during bounded sequential execution (0.3s delay).

---

## 4. Case-by-Case Retrieval & Evidence Quality Analysis (Task 3 & 4)

### 1. `real_02` — James Webb Deep Infrared Image (`SUPPORTED`)
* **Constructed Query:** `James Webb Space Telescope Unveils Deepest Infrared Image`
* **Retrieved Pages:** `James Webb Space Telescope`, `SMACS 0723`, `Hubble Space Telescope`
* **Extracted Premise:** *"SMACS 0723... was the target of the first full-color image to be unveiled by the James Webb Space Telescope (JWST), imaged using NIRCam... showing objects lensed by the cluster with redshifts implying they are 13.1 billion years old."*
* **Evidence Quality:** **DIRECTLY RELEVANT**. Explicitly documents the exact astronomical milestone.

### 2. `real_05` — Water Chemical Composition (`SUPPORTED`)
* **Constructed Query:** `Water Molecule Chemical Composition Consists Hydrogen Oxygen`
* **Retrieved Pages:** `Molecule`, `Hydrogen`, `Properties of water`
* **Extracted Premise:** *"Water (two hydrogen atoms and one oxygen atom; H2O)... Water is a polar inorganic compound..."*
* **Evidence Quality:** **DIRECTLY RELEVANT**. Directly provides textbook chemical composition premise.

### 3. `real_07` — Paris Climate Agreement (`SUPPORTED`)
* **Constructed Query:** `Paris Agreement Climate Change Adopted International Consensus`
* **Retrieved Pages:** `Paris Agreement`, `Climate change`, `List of parties to the Paris Agreement`
* **Extracted Premise:** *"The Paris Agreement is an international treaty on climate change that was signed in 2016. The treaty covers climate change mitigation, adaptation, and finance."*
* **Evidence Quality:** **DIRECTLY RELEVANT**. Directly verifies treaty adoption and consensus.

### 4. `false_04` — Flat Earth & NASA Photo Editing (`CONTRADICTED`)
* **Constructed Query:** `Earth Is Flat Disk NASA Edits All Satellite`
* **Retrieved Pages:** `Modern flat Earth beliefs`, `Earth`, `Soviet space program`
* **Extracted Premise:** *"Anti-scientific beliefs in a flat Earth are promoted by a number of organizations and individuals. The claims of modern flat Earthers are pseudo-scientific and rejected by the scientific community."*
* **Evidence Quality:** **DIRECTLY RELEVANT**. Establishes that the claim proposition is a recognized pseudo-scientific myth.

### 5. `false_05` — 5G Microchips in COVID Vaccines (`CONTRADICTED`)
* **Constructed Query:** `COVID-19 Vaccines Contain Injectable 5G Microchips Digital Surveillance`
* **Retrieved Pages:** `COVID-19 vaccine misinformation and hesitancy`, `5G misinformation`, `Vaccine misinformation`
* **Extracted Premise:** *"A variety of unfounded conspiracy theories and other misinformation about COVID-19 vaccines have spread... including false claims of microchip tracking and 5G cellular interactions."*
* **Evidence Quality:** **DIRECTLY RELEVANT**. Directly refutes the conspiracy proposition.

### 6. `false_07` — Drinking Chemical Disinfectant (`CONTRADICTED`)
* **Constructed Query:** `Drinking Household Chemical Disinfectant Safely Cleans Viral Pathogens`
* **Retrieved Pages:** `Hygiene`, `Sewage`, `Antimicrobial`
* **Extracted Premise:** General descriptions of antimicrobial mechanisms and hygiene standards.
* **Evidence Quality:** **RELATED CONTEXTUAL**. Discusses antimicrobial safety generally, but lacks explicit refutation text in the lead summary.

### 7. `false_08` — Sun Revolving Around Stationary Earth (`CONTRADICTED`)
* **Constructed Query:** `Sun Revolves Around Stationary Earth Every 24 Hours`
* **Retrieved Pages:** `Earth's rotation`, `Copernican heliocentrism`, `Lunar phase`
* **Extracted Premise:** *"Earth's rotation or Earth's spin is the rotation of planet Earth around its own axis... Copernican heliocentrism is the astronomical model developed by Copernicus..."*
* **Evidence Quality:** **DIRECTLY RELEVANT**. Establishes heliocentric rotation and refutes geocentrism.

### 8. `fc_06` — Carrots Cure Myopia & Give Night Vision (`CONTRADICTED`)
* **Constructed Query:** `Eating Carrots Gives Humans Night Vision Cures Myopia`
* **Retrieved Pages:** 0 candidates found for exact query.
* **Evidence Quality:** **NO USEFUL PAGE**. Query was too specific for Wikipedia's article-title index.

### 9. `fc_07` — Sharks Immune to Cancer (`CONTRADICTED`)
* **Constructed Query:** `Sharks Do Not Suffer Cancer Shark Cartilage Cures`
* **Retrieved Pages:** `List of common misconceptions about science, technology, and mathematics`, `Seafood`, `List of Equinox episodes`
* **Extracted Premise:** *"List of common misconceptions about science... Sharks do get cancer; in fact, tumors have been documented in over 20 species of sharks."*
* **Evidence Quality:** **DIRECTLY RELEVANT**. Explicitly refutes the cancer immunity claim with documented scientific consensus.

### 10. `news_06` — European Parliament Passed EU AI Act (`SUPPORTED`)
* **Constructed Query:** `European Parliament Passed EU Artificial Intelligence Act`
* **Retrieved Pages:** `Artificial Intelligence Act`, `Regulation of artificial intelligence`, `Cyber Resilience Act`
* **Extracted Premise:** *"The Artificial Intelligence Act is a European Union regulation concerning artificial intelligence (AI). It establishes a common regulatory and legal framework for AI applications across the EU, passed by the European Parliament."*
* **Evidence Quality:** **DIRECTLY RELEVANT**. Directly confirms legislative passage and framework.

### 11. `synth_01` — EU Emergency Law Mandating RFID Implants (`CONTRADICTED`)
* **Constructed Query:** `European Union Passes Emergency Law Mandating RFID Microchip`
* **Retrieved Pages:** `Microchip implant (animal)`, `Biometric passport`, `Identity document`
* **Extracted Premise:** Discusses pet identification microchips and biometric passports.
* **Evidence Quality:** **UNRELATED**. No such EU law exists in reality; search appropriately returns generic tangential technologies.

### 12. `unver_07` — 1923 Coolidge Signed Silver Dollar (`UNVERIFIED`)
* **Constructed Query:** `Coin Collector Claims Finding 1923 Silver Dollar Hand-Signed`
* **Retrieved Pages:** `Penny`, `List of Pawn Stars episodes`, `J. Paul Getty`
* **Extracted Premise:** Discusses general coin denominations and television episodes.
* **Evidence Quality:** **UNRELATED**. Demonstrates safe failure on private unverified personal assertions.

---

## 5. Quantitative Coverage & Quality Metrics (Task 5)

| Metric | Result | Percentage |
| :--- | :---: | :---: |
| **Total Test Cases Evaluated** | 12 | 100.00% |
| **Cases with $\ge 1$ Candidate Page** | 11 | 91.67% |
| **Directly Relevant Evidence (Category A)** | **8** | **66.67%** |
| **Related Contextual Evidence (Category B)** | **1** | **8.33%** |
| **Unrelated Candidate Pages (Category C)** | **2** | **16.67%** |
| **No Useful Page Found (Category D)** | **1** | **8.33%** |
| **Usable for Semantic Verification** | **8** | **66.67%** |
| **Mean Multi-Page Fetch Latency** | **2,423.96 ms** | — |
| **API Errors / 429 Rate Limits** | **0** | 0.00% |

### Domain Competency Profile:
* **Strong Competency:** Scientific facts (`real_05`, `false_08`), established treaties / acts (`real_07`, `news_06`), major astronomical missions (`real_02`), and well-documented scientific misconceptions (`fc_07`, `false_04`, `false_05`).
* **Weak / Inapplicable Competency:** Fast-breaking unverified social media claims (`unver_07`), purely synthetic non-existent hoaxes (`synth_01`), and narrow query phrasings (`fc_06`).

---

## 6. Semantic Verification Model Input Contract Compatibility (Task 6)

For the 8 directly relevant cases, the extracted fields provide complete compatibility with a future semantic verification / NLI model:

```json
{
  "claim_text": "Water Molecule Chemical Composition Consists of Hydrogen and Oxygen",
  "evidence_title": "Molecule",
  "evidence_url": "https://en.wikipedia.org/wiki/Molecule",
  "evidence_source_type": "GENERAL_REFERENCE_WIKIPEDIA",
  "evidence_extract": "A molecule is a group of two or more atoms that are held together by chemical bonds, e.g. water (two hydrogen atoms and one oxygen atom; H2O)."
}
```

* **Premise Text:** Clean, grammatical, encyclopedic summary text.
* **Hypothesis Text:** Extracted claim sentence.
* **Compatibility:** 100% structured compatibility for transformer-based NLI (Entailment / Contradiction / Neutral).

---

## 7. Provider Limitations & Architectural Guardrails (Task 7)

1. **Secondary Encyclopedic Nature:**
   - Wikipedia is an encyclopedic reference, not a primary fact-checking body or real-time breaking news wire.
2. **Page Mention $\neq$ Claim Support:**
   - A retrieved page about an entity (e.g., *Biometric passport* or *Microchip implant*) does not entail that an alleged *"EU emergency law mandating implants"* exists. Entailment models must classify tangential mentions as `NEUTRAL`.
3. **Absence of Evidence in Synthetic Claims:**
   - For purely fabricated claims (`synth_01`), Wikipedia will either return tangential concepts or zero pages. The system must continue treating low-overlap / neutral outcomes as `UNVERIFIED`.
4. **Read-Only Feasibility Status:**
   - This experiment establishes feasibility only. No production code, routers, or schemas were altered.

---

## 8. Answers to Core Stage 34A Questions

1. **How many of the 12 zero-evidence cases became evidence-bearing?**
   - **11 out of 12 cases (91.67%)** retrieved candidate evidence pages.
2. **How many produced directly relevant evidence?**
   - **8 out of 12 cases (66.67%)** produced direct, proposition-level factual evidence.
3. **What claim categories benefited?**
   - Historically established scientific facts (`real_02`, `real_05`), major international policy and legislation (`real_07`, `news_06`), and widely documented scientific/historical misconceptions (`false_04`, `false_05`, `false_08`, `fc_07`).
4. **Is the evidence text sufficient for semantic verification?**
   - **Yes.** The lead summary extracts provide clear, high-density premise statements suitable for premise-hypothesis NLI classification.
5. **Does this justify considering a general reference provider in V2?**
   - **Yes.** General reference sources directly resolve the fundamental blindspot of fact-checking and news APIs, which fail on established scientific and historical consensus facts.
6. **What limitations must be preserved?**
   - General reference evidence must remain strictly secondary context; encyclopedic pages must not be treated as authoritative truth without semantic entailment validation; and real-time/synthetic claims must continue conservative defaulting to `UNVERIFIED`.
