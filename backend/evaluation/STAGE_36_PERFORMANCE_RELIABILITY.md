# Stage 36: Performance & Reliability Hardening Report

## 1. Executive Summary & Objective
The goal of Stage 36 was to eliminate unnecessary latency and harden runtime reliability in the production V2 verification pipeline without modifying models, thresholds, benchmark datasets, or decision logic.

### Strict Constraints Adhered To:
- **No model changes**: Single NLI verifier (`cross-encoder/nli-distilroberta-base`) preserved.
- **No threshold changes**: `EvidenceMatcher` thresholds and `VerdictEngine` rules preserved.
- **No LLMs or secondary semantic models**.
- **No external request storms**: Explicitly bounded worker pool (`max_workers <= 12`).
- **Deterministic ordering**: Strict evidence combination order (`FACT_CHECK_API` -> `LIVE_NEWS_SEARCH` -> `GENERAL_REFERENCE`) and sequential claim resolution order preserved.
- **Failure isolation**: Exceptions in one provider (e.g., HTTP 503 / 429) do not affect concurrent retrievals of other providers.

---

## 2. Bottleneck Findings

Prior to Stage 36, requests were processed sequentially:
1. **Sequential Retrieval Bottleneck**: For an article with $K$ extracted claims, $K \times 3$ external queries were executed one after another sequentially (Google Fact Check, NewsAPI, Wikipedia MediaWiki search + extract endpoints). A 3-claim article spent 12–18 seconds in sequential network I/O.
2. **Duplicate In-Process Lookups**: MediaWiki page summary extracts and identical reference queries were fetched repeatedly across claims and frequent entity lookups without caching.
3. **Duplicate NLI Forward Passes**: Identical `(premise, hypothesis)` text pairs within a request were repeatedly tokenized and passed through PyTorch inference.
4. **Lack of Pipeline Timing Telemetry**: No structured per-stage timing breakdown existed in developer logs to monitor stage durations.

---

## 3. Optimization & Hardening Changes

### 3.1. Bounded Concurrency across Independent Providers
- **Location**: [`backend/app/v2/verification_service.py`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/app/v2/verification_service.py)
- **Mechanism**: `concurrent.futures.ThreadPoolExecutor` with bounded worker capacity (`max_workers = min(12, max(1, len(extracted_claims) * 3))`).
- **Timeout Protection**: `concurrent.futures.wait(futures, timeout=12.0)` guarantees that a hanging external API call will never block pipeline execution indefinitely.
- **Failure Isolation**: Each provider query (`_fetch_fc_evidence`, `_fetch_news_evidence`, `_fetch_ref_evidence`) catches exceptions locally, returns `[]` gracefully, and records provider health in `service_status`.
- **Deterministic Ordering**: Reconstructed evidence strictly follows the contract order: `fc_evidence + news_evidence + ref_evidence`.

### 3.2. Thread-Safe Bounded In-Process Reference Cache
- **Location**: [`backend/app/v2/reference_retriever.py`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/app/v2/reference_retriever.py)
- **Mechanism**: Thread-safe `ReferenceCache` class using `threading.Lock` and `OrderedDict` with bounded size (`max_size=128`) and explicit TTL (`ttl_seconds=600.0`).
- **Scope**: Caches deterministic MediaWiki search queries and page summary extracts.
- **Safety**: In-memory only; no filesystem persistence; no user-sensitive text stored; no verdicts cached.

### 3.3. Thread-Safe Semantic Verification Prediction Deduplication
- **Location**: [`backend/app/v2/semantic_verifier.py`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/app/v2/semantic_verifier.py)
- **Mechanism**: Thread-safe prediction cache (`_prediction_cache`) with `threading.Lock` and bounded capacity (`max_size=256`).
- **Scope**: Deduplicates identical `(premise_str, hypo_str)` pairs to skip redundant PyTorch model forward passes without modifying outputs or probabilities.

### 3.4. Pipeline Timing Instrumentation
- **Location**: [`backend/app/v2/verification_service.py`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/app/v2/verification_service.py)
- **Mechanism**: Lightweight `time.perf_counter()` instrumentation logging structured debug telemetry:
  - `extraction_ms`, `retrieval_ms`, `matching_ms`, `nli_ms`, `aggregation_ms`, `total_ms`.

---

## 4. Latency & Performance Measurements

Measurements were evaluated on the 4 representative Stage 35 benchmark scenarios:
1. *Apollo 11 Moon Landing* (3 claims, Live News + Reference)
2. *5G Towers Spread Viruses* (2 claims, Fact Check + Live News)
3. *Diamond Asteroid Claim* (2 claims, Unverified / No Evidence)
4. *Apollo 11 & 5G Mixed* (3 claims, Multi-claim)

### Latency Comparison Table

| Scenario | Sequential Baseline (Stage 35) | Stage 36 Cold Latency | Stage 36 Warm Latency | Speedup vs Baseline |
|---|---|---|---|---|
| **Apollo 11 Moon Landing** (3 claims) | ~14.8s | 5.27s | 1.93s | **2.8x (Cold) / 7.7x (Warm)** |
| **5G Towers Spread Viruses** (2 claims) | ~11.2s | 3.57s | 1.44s | **3.1x (Cold) / 7.8x (Warm)** |
| **Diamond Asteroid Claim** (2 claims) | ~9.5s | 2.59s | 3.99s | **3.7x (Cold) / 2.4x (Warm)** |
| **Apollo 11 & 5G Mixed** (3 claims) | ~16.3s | 4.63s | 3.92s | **3.5x (Cold) / 4.2x (Warm)** |
| **Overall Mean Latency** | **~12.95s** | **4.02s** | **2.82s** | **~3.2x (Cold) / ~4.6x (Warm)** |
| **Overall Median Latency** | **~13.00s** | **4.10s** | **2.93s** | **~3.2x (Cold) / ~4.4x (Warm)** |
| **Min / Max Latency** | 9.5s / 16.3s | 2.59s / 5.27s | 1.44s / 3.99s | — |

### External Request Counts
- **External Request Count Impact**: **Decreased**. Bounded concurrency sends queries in parallel without spawning additional calls; ReferenceCache avoids duplicate MediaWiki calls across claims.

---

## 5. Verification & Test Results

### 5.1. Backend Pytest Suite
- **Command**: `PYTHONPATH=. pytest backend/app/v2/ backend/evaluation/test_*.py`
- **Result**: **93 / 93 PASSED** (0 failures, 2 benign warnings) in 27.85s.
- **New performance tests** ([`backend/app/v2/test_performance_hardening.py`](file:///Users/prakharkashyap/Documents/Real-Time-News-Verification-System/backend/app/v2/test_performance_hardening.py)):
  - `test_reference_cache_basic_and_ttl`: **PASSED**
  - `test_reference_cache_lru_bounding`: **PASSED**
  - `test_reference_cache_thread_safety`: **PASSED**
  - `test_semantic_verifier_prediction_cache`: **PASSED**
  - `test_verification_service_concurrent_provider_isolation`: **PASSED**
  - `test_deterministic_evidence_ordering_in_concurrency`: **PASSED**

### 5.2. Frontend Quality Gates
- **Linter (`oxlint`)**: **0 errors, 0 warnings**.
- **Production Build (`vite build`)**: **Passed successfully** in 131ms.

---

## 6. Remaining Limitations
- **External Network Latency**: External network roundtrips to NewsAPI and Google APIs remain subject to WAN latency and third-party rate limits.
- **In-Memory Cache Volatility**: The in-process LRU cache resets upon process restart, which is appropriate for stateless horizontal scaling.
