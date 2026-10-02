# Real-Time News & Claim Verification System

A multi-stage real-time news and claim verification system combining multi-source evidence retrieval (Google Fact Check Tools API, NewsAPI, and Wikipedia Reference) with lexical-semantic relevance filtering, Natural Language Inference (NLI) stance analysis, deterministic verdict synthesis, and an auxiliary linguistic style signal.

---

## 1. Project Overview

The **Real-Time News & Claim Verification System** evaluates the factual accuracy of news headlines and article claims against real-world evidence sources.

Traditional machine learning classifiers evaluate text solely on stylistic or lexical patterns. This system implements an evidence-first architecture: extracting key factual assertions, querying fact-checking databases, live news articles, and general reference encyclopedias, evaluating proposition relevance, performing cross-encoder NLI stance inference, and synthesizing a grounded final verdict (`SUPPORTED`, `CONTRADICTED`, or `UNVERIFIED`).

---

## 2. Evolution: V1 Stylistic Classifier to V2 Evidence Pipeline

### V1 Architecture (Stylistic Text Classification)
- **Pipeline**: Text Preprocessing → TF-IDF Unigram/Bigram Vectorization → LinearSVC Classifier trained on the WELFake dataset (63,672 records).
- **Function**: Detected statistical writing style patterns associated with fake vs. real news.
- **Role in V2**: The V1 LinearSVC model serves strictly as an **auxiliary linguistic signal**. It provides stylistic context but does not determine factual truth, cannot override external evidence, and is never used as the sole basis for a verdict.

### Why V2 Was Introduced
Linguistic style is not a proxy for factual truth:
- Misinformation can be written in polished, formal journalistic prose.
- Legitimate breaking news may exhibit informal or urgent stylistic traits.
- Static classifiers cannot verify dynamic real-world facts or check claims against fact-checking organizations.

---

## 3. V2 Architecture & Verification Flow

The V2 pipeline evaluates news claims across six sequential stages:

```
User Input (Headline & Article Text)
  │
  ▼
1. Claim Extraction ──────────► Extracts core factual assertions & generates search queries
  │
  ▼
2. Multi-Source Retrieval ────► Queries Google Fact Check API, NewsAPI, and Wikipedia Reference
  │
  ▼
3. Evidence Matching ─────────► Filters retrieved evidence by text similarity & entity/temporal guardrails
  │
  ▼
4. Semantic NLI Verification ─► cross-encoder/nli-distilroberta-base (SUPPORTS / CONTRADICTS / NEUTRAL)
  │
  ▼
5. Auxiliary Linguistic Signal ► Computes V1 LinearSVC stylistic prediction as informational context
  │
  ▼
6. Verdict Engine ────────────► Synthesizes evidence consensus into final verdict
  │
  ▼
Output: Final Verdict (SUPPORTED / CONTRADICTED / UNVERIFIED) + Evidence Items + Linguistic Signal
```

### Component Breakdown
1. **Claim Extraction**: Parses submitted text into discrete, verifiable factual claims and formulates search queries.
2. **Multi-Source Retrieval**:
   - **Google Fact Check Tools API**: Retrieves assessments from verified fact-checking organizations (Snopes, PolitiFact, Full Fact, BOOM, AFP, etc.).
   - **NewsAPI**: Retrieves global reporting for breaking and contemporary news.
   - **Wikipedia General Reference**: Retrieves encyclopedic reference articles for established scientific and historical claims.
3. **EvidenceMatcher**: Evaluates keyword overlap, token similarity, and proposition alignment while applying entity and temporal boundary checks to prevent topical leakage.
4. **Semantic NLI Verifier**: Applies `cross-encoder/nli-distilroberta-base` to evaluate entailment relationships between claim propositions and evidence snippets into `SUPPORTS`, `CONTRADICTS`, or `NEUTRAL`.
5. **Verdict Engine**: Evaluates evidence strength, stance consensus, and source conflicts to produce `SUPPORTED`, `CONTRADICTED`, or `UNVERIFIED`.
6. **Auxiliary Signal**: Integrates the V1 LinearSVC signal as non-verdict informational metadata.

---

## 4. Verdict Definitions

| Verdict | Meaning | Decision Criteria |
|---|---|---|
| **`SUPPORTED`** | Verified True | Strong, credible evidence or fact-checker consensus confirms the claim proposition. |
| **`CONTRADICTED`** | Verified False / Debunked | Authoritative fact-checkers or credible reporting directly refute or debunk the claim. |
| **`UNVERIFIED`** | Inconclusive / Insufficient Evidence | No relevant external evidence was found, evidence is conflicting, or available sources lack consensus. |

> [!IMPORTANT]
> **Important Note on `UNVERIFIED`:**
> An `UNVERIFIED` assessment indicates that the system found insufficient, inconclusive, or conflicting external evidence to reach an authoritative determination. It does **not** mean the claim is false.

---

## 5. Technology Stack

- **Backend Framework**: Python 3.10+, FastAPI, Pydantic v2, Uvicorn
- **Semantic Inference & NLP**: PyTorch, HuggingFace Transformers (`cross-encoder/nli-distilroberta-base`), Scikit-Learn
- **External Retrieval APIs**:
  - Google Fact Check Tools Claim Search API
  - NewsAPI.org (`/v2/everything`)
  - Wikipedia Action API (MediaWiki REST/Action)
- **Frontend**: React 19, Vite, Axios, Vanilla CSS (Glassmorphism design, responsive layouts)
- **Evaluation & Testing**: Pytest, TestClient

---

## 6. Stage 40 Final Real-World Benchmark Results

The final real-world benchmark was evaluated against the full 64-case / 136-claim dataset across 8 categories:

- **Total Benchmark Cases:** 64
- **Total Claims Extracted:** 136
- **Overall Ground-Truth Accuracy:** **46.88%** (30 / 64 correct verdicts)
- **Macro F1:** **35.56**
- **Weighted F1:** **40.03**
- **CONTRADICTED Recall / Precision / F1:** **47.83%** (11/23) / **57.89%** (11/19) / **52.38**
- **UNVERIFIED Recall / Precision / F1:** **76.00%** (19/25) / **42.22%** (19/45) / **54.29**
- **SUPPORTED Recall:** **0.00%** (0/16)
- **False Positive Rate for CONTRADICTED:** **19.51%** (8 / 41 non-CONTRADICTED cases predicted as CONTRADICTED)
- **False Negative Rate for CONTRADICTED:** **52.17%** (12 / 23)
- **False Negative Rate for SUPPORTED:** **100.00%** (16 / 16)
- **Conflict Rate:** **4.69%** (3 cases)
- **Accepted Evidence Items:** **123** (29 Google Fact Check, 8 NewsAPI, 86 Wikipedia Reference)
- **Latency (Mean / Median / P95):** 3,304 ms / 3,159 ms / 4,943 ms

### 3x3 Confusion Matrix
```text
                 Pred SUPPORTED  Pred CONTRADICTED  Pred UNVERIFIED  Total
  GT SUPPORTED          0                2                 14          16
  GT CONTRADICTED       0               11                 12          23
  GT UNVERIFIED         0                6                 19          25
  Total                 0               19                 45          64
```

---

## 7. Known Limitations

1. **SUPPORTED Recall (0.00%):** General reference text (Wikipedia) and news coverage often provide descriptive or background context rather than explicit affirmative confirmation of specific claim assertions. Without domain-specific knowledge graphs, positive verification remains conservative.
2. **External API Quota Constraints:** The NewsAPI Developer tier is limited to 100 requests per 24 hours. The evaluation runner enforces a quota-safe budget of 99 benchmark requests (with 37 claims evaluated via Fact Check and Wikipedia Reference).
3. **Temporal Sensitivity:** Emerging news stories require real-time indexing. If a story has not yet been indexed by NewsAPI or evaluated by fact-checkers, the system conservatively returns `UNVERIFIED`.

---

## 8. Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
# Clone the repository
git clone https://github.com/PrakharKashyap21/Real-Time-News-Verification-System.git
cd Real-Time-News-Verification-System

# Install Python dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp backend/env.example backend/.env
# Edit backend/.env with your GOOGLE_FACT_CHECK_API_KEY and NEWS_API_KEY

# Start the FastAPI backend server
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8008 --reload
```

### 2. Frontend Setup
```bash
# In a separate terminal
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

### 3. Running Automated Tests
```bash
# Run backend unit and evaluation test suite
PYTHONPATH=. pytest backend/app/v2/ backend/evaluation/test_*.py

# Run frontend lint and build checks
cd frontend && npm run lint && npm run build
```

---

## 9. API Endpoints

- `GET /`: Service information and status.
- `GET /health`: System health check and model availability.
- `POST /predict`: V1 standalone stylistic text classification endpoint.
- `POST /v2/verify`: V2 full evidence-based verification pipeline.
