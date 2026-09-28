# Stage 34C — Semantic Verification Model Feasibility Report

## 1. Executive Summary

This feasibility evaluation prototypes and evaluates **ONE standalone pretrained Natural Language Inference (NLI) model** for claim-versus-evidence reasoning. The goal is to determine whether an NLI cross-encoder can replace rigid lexical heuristics and accurately classify proposition-level semantic relations (`SUPPORTS`, `CONTRADICTS`, `NEUTRAL`) across real-world evidence and benchmark failure cases documented in this project.

### Key Feasibility Findings:
* **Selected Model:** `cross-encoder/nli-distilroberta-base` (82M parameters, 328 MB).
* **Controlled Evaluation Set:** 24 balanced claim-evidence pairs (8 Clear Support, 8 Clear Contradiction, 8 Neutral/Adjacent).
* **Overall Accuracy:** **70.83% (17 / 24 correct)**.
* **Macro F1 Score:** **0.7111**.
* **Clear Support (Entailment) Recognition:** **87.5% (7/8 correct)** — Precision: **1.000**, Recall: **0.875**, F1: **0.9333**.
* **Clear Contradiction Recognition:** **75.0% (6/8 correct)** — Precision: **0.600**, Recall: **0.750**, F1: **0.6667**.
* **Adjacent / Neutral Rejection:** **50.0% (4/8 correct)** — Precision: **0.5714**, Recall: **0.500**, F1: **0.5333**.
* **Inference Latency:** **Median 15.47 ms** per pair on local CPU (Mean: 29.51 ms including first warm-up; 95th percentile: 18.20 ms).
* **Model Loading Time:** ~6.62 seconds.

---

## 2. Model Selection & Architecture (Task 1)

* **Model Name:** `cross-encoder/nli-distilroberta-base`
* **Source Library:** Hugging Face `transformers` & `torch`
* **Architecture:** DistilRoBERTa cross-encoder fine-tuned on Stanford Natural Language Inference (SNLI) and Multi-Genre NLI (MultiNLI) datasets.
* **Parameter Count:** 82 million parameters (~328 MB `model.safetensors`).
* **Hardware Requirements:** Runs fully locally on CPU without GPU acceleration or external API dependencies.
* **Rationale for Selection:**
  1. True cross-encoder architecture allows full bidirectional cross-attention between premise and hypothesis tokens.
  2. Extremely lightweight with sub-20ms CPU latency.
  3. Direct 3-class NLI logit outputs corresponding to canonical semantic relations without generative hallucination risks.

---

## 3. Input/Output Contract & Stance Mapping (Task 2 & 6)

### Input Contract:
* **Premise:** Extracted evidence snippet or encyclopedic extract text (e.g. from Google Fact Check, NewsAPI, or Wikipedia).
* **Hypothesis:** Extracted user claim proposition.

### Model Output & Deterministic Stance Mapping:
The raw model outputs 3 logits corresponding to the native id2label mapping: `{0: 'contradiction', 1: 'entailment', 2: 'neutral'}`.

$$\text{Predicted Relation} = \begin{cases} \text{SUPPORTS} & \text{if } \operatorname{argmax}(\text{logits}) = \text{'entailment'} \\ \text{CONTRADICTS} & \text{if } \operatorname{argmax}(\text{logits}) = \text{'contradiction'} \\ \text{NEUTRAL} & \text{if } \operatorname{argmax}(\text{logits}) = \text{'neutral'} \end{cases}$$

> [!IMPORTANT]
> Raw model logits and softmax probabilities are preserved solely for diagnostic inspection and uncertainty calibration. They are **never** converted into an arbitrary "truth probability."

---

## 4. Controlled 24-Pair Evaluation Results (Task 3, 5, 7)

### Evaluation Metrics Summary:

| Metric | Score | Detail |
| :--- | :---: | :--- |
| **Total Test Pairs** | 24 | Balanced (8 Support, 8 Contradict, 8 Neutral) |
| **Overall Accuracy** | **70.83%** | 17 / 24 correct |
| **Macro F1** | **0.7111** | Balanced across all 3 classes |
| **Support Recognition Accuracy** | **87.50%** | 7 / 8 true supports identified |
| **Contradiction Recognition Accuracy** | **75.00%** | 6 / 8 true contradictions identified |
| **Adjacent Neutral Rejection Accuracy**| **50.00%** | 4 / 8 adjacent neutrals safely rejected |
| **Median Inference Latency** | **15.47 ms** | Local CPU |
| **P95 Latency** | **18.20 ms** | Local CPU |

### Confusion Matrix:

```
                  Predicted SUPPORTS   Predicted CONTRADICTS   Predicted NEUTRAL   Total
Actual SUPPORTS            7                     0                     1             8
Actual CONTRADICTS         0                     6                     2             8
Actual NEUTRAL             0                     4                     4             8
Total Predicted            7                    10                     7            24
```

### Per-Class Precision, Recall, and F1:

| Semantic Relation | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **SUPPORTS** | 7 | 0 | 1 | **1.0000** | **0.8750** | **0.9333** |
| **CONTRADICTS** | 6 | 4 | 2 | **0.6000** | **0.7500** | **0.6667** |
| **NEUTRAL** | 4 | 3 | 4 | **0.5714** | **0.5000** | **0.5333** |

---

## 5. Real Project Failure Cases Analysis (Task 4)

The model was evaluated specifically against failure cases documented in Stage 33A, Stage 33D, and Stage 34A:

| Case ID / Target | Evidence Premise Text | Claim Hypothesis | Ground Truth | Model Prediction | Result | Analysis |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `real_04` (Apollo 11 Debunk) | Fact Check: The Apollo 11 moon landing was not staged. Neil Armstrong and Buzz Aldrin landed the Lunar Module on the Moon in July 1969. | *Apollo 11 Astronauts Landed on Moon in July 1969* | SUPPORTS | **SUPPORTS** | **SUCCESS** | Correctly resolves fact-check refuting a hoax into historical support. |
| `fc_05` (EU Combustion Cars) | The European Parliament and EU member states approved legislation mandating zero emissions for new cars, banning new internal combustion engine cars from 2035. | *European Union Bans Internal Combustion Engine Cars by 2035* | SUPPORTS | **SUPPORTS** | **SUCCESS** | Correctly maps legislative text to claim assertion. |
| `real_05` (Water Molecule) | Water is a chemical compound consisting of two hydrogen atoms and one oxygen atom (H2O). | *Water Molecule Chemical Composition Consists of Hydrogen and Oxygen* | SUPPORTS | **SUPPORTS** | **SUCCESS** | Stage 34A encyclopedic extract directly entails textbook claim. |
| `real_07` (Paris Agreement) | The Paris Agreement is an international treaty on climate change adopted by international consensus in 2015 and signed in 2016. | *Paris Agreement on Climate Change Adopted by International Consensus* | SUPPORTS | **SUPPORTS** | **SUCCESS** | Stage 34A treaty summary entails adoption claim. |
| `false_05` (5G Microchips) | Public health agencies confirm COVID-19 vaccines contain mRNA or viral vectors without microchips, 5G tracking hardware, or electronic devices. | *COVID-19 Vaccines Contain Injectable 5G Microchips for Digital Surveillance* | CONTRADICTS | **CONTRADICTS** | **SUCCESS** | Directly refutes conspiracy claim proposition. |
| `real_08` (CRISPR Vaccine Debunk) | Fact Check: COVID-19 mRNA vaccines do not contain CRISPR-Cas9 gene editing tools and do not permanently modify human DNA. | *CRISPR-Cas9 gene editing technology was developed by Emmanuelle Charpentier and Jennifer Doudna* | NEUTRAL | **NEUTRAL** | **SUCCESS** | Correctly identifies that vaccine-CRISPR hoax debunk is unrelated to Charpentier/Doudna invention. |
| `real_02` (JWST Chorizo Hoax) | A viral photograph claiming to show the first star image captured by the JWST was actually a slice of Spanish chorizo sausage on a black background. | *James Webb Space Telescope Unveils Deepest Infrared Image of Universe* | NEUTRAL | **CONTRADICTS** | **FAILURE** | The model over-indexes on negative debunk tokens ("actually a slice of chorizo") and predicts contradiction instead of neutral. |
| `real_01` (Voyager Thruster Glitch) | NASA's Voyager 1 spacecraft experienced a thruster glitch in 2024 and engineers switched to a backup thruster branch. | *NASA Voyager 1 Reached Interstellar Space in August 2012* | NEUTRAL | **CONTRADICTS** | **FAILURE** | The model confuses same-entity different-time events as mutually contradictory. |

---

## 6. Detailed Limitation & Failure Mode Analysis (Task 8)

1. **Debunk Marker Leakage (Adjacent Hoax Bias):**
   When an evidence premise contains strong debunking vocabulary (e.g. *falsely, fake, hoax, unproven*) directed at an *adjacent proposition*, standard NLI models often predict `CONTRADICTION` for the entire hypothesis even when the user claim is completely orthogonal.
2. **Temporal & Event Disconnection:**
   The model lacks intrinsic temporal awareness (e.g., distinguishing an event in 1969 vs 2024). It treats two distinct events involving the same entity (*"Voyager thruster glitch in 2024"* vs *"Voyager reached interstellar space in 2012"*) as contradictory rather than independent/neutral.
3. **High Precision on Direct Support (100%):**
   Zero false positives were observed for `SUPPORTS`. When the model predicts `SUPPORTS`, the entailment is genuinely valid.
4. **Asymmetry in Contradiction Precision (60%):**
   Because neutral adjacent text is often misclassified as contradiction, using raw NLI predictions without lexical entity-matching guardrails would cause false contradiction verdicts on neutral news.

---

## 7. Suitability for Future V2 Verification Pipeline

### Feasibility Conclusion:
The `cross-encoder/nli-distilroberta-base` model is **HIGHLY SUITABLE** as a semantic entailment verifier for a future multi-stage architecture, subject to two design constraints:
1. **Never use NLI in isolation:** It must be paired with the existing deterministic [`EvidenceMatcher`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/app/v2/evidence_matcher.py#L30-L425) entity/predicate filter to discard off-topic evidence *before* inference.
2. **Calibrated Thresholds:** To prevent false contradictions from adjacent debunking language, the verifier should require high logit margin for `CONTRADICTION` or fall back to `NEUTRAL`.
