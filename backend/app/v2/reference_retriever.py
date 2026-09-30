import os
import re
import json
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
from collections import OrderedDict
from typing import List, Optional, Dict, Any, Tuple
from backend.app.v2.schemas import (
    EvidenceItem,
    ExtractedClaim,
    EvidenceSourceType,
    StanceType
)
from backend.app.v2.query_builder import get_query_builder, FactCheckQueryBuilder


class ReferenceCache:
    """Thread-safe bounded in-memory LRU cache with TTL for general reference lookups."""

    def __init__(self, max_size: int = 128, ttl_seconds: float = 600.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            val, timestamp = self._cache[key]
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return val

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time())
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class ReferenceRetrieverError(RuntimeError):
    """Base exception for general reference retriever errors."""
    pass


class ReferenceRetrieverAPIError(ReferenceRetrieverError):
    """Raised when MediaWiki API returns an HTTP error status."""
    def __init__(self, status_code: int, message: str):
        super().__init__(f"MediaWiki API error (HTTP {status_code}): {message}")
        self.status_code = status_code
        self.message = message


class ReferenceRetrieverRateLimitError(ReferenceRetrieverAPIError):
    """Raised when MediaWiki API returns HTTP 429 rate limit status."""
    def __init__(self, message: str = "MediaWiki rate limit exceeded (HTTP 429)"):
        super().__init__(429, message)


class ReferenceRetrieverTimeoutError(ReferenceRetrieverError):
    """Raised when MediaWiki request times out."""
    pass


class ReferenceRetrieverMalformedResponseError(ReferenceRetrieverError, ValueError):
    """Raised when MediaWiki returns non-parseable or malformed JSON."""
    pass


def strip_html_tags(text: Optional[str]) -> str:
    """Removes HTML markup (such as search match spans) from text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def extract_relevant_passage(
    claim: ExtractedClaim,
    page_title: str,
    full_extract: str,
    search_snippet: str = ""
) -> str:
    """Selects a concise, claim-specific 1-2 sentence evidence passage from reference text.

    Avoids broad multi-paragraph extracts by scoring candidate sentences against the claim's
    entities, action predicates, and substantive proposition terms.
    """
    if not full_extract:
        return search_snippet.strip()

    text = full_extract.strip()
    # Split on sentence boundaries
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text) if s.strip()]
    if not sentences:
        return search_snippet.strip() or text
    if len(sentences) == 1:
        return sentences[0]

    # Tokenize claim for scoring
    claim_text = (claim.text or "").strip().lower() if claim else ""
    claim_tokens = set(re.findall(r"\b[a-z0-9'-]{3,}\b", claim_text))
    common_sw = {
        "the", "and", "that", "this", "with", "from", "for", "was", "were",
        "been", "have", "has", "had", "are", "which", "who", "whom", "its"
    }
    substantive_claim_tokens = claim_tokens - common_sw

    if not substantive_claim_tokens:
        return sentences[0]

    candidates = []
    # Single sentences
    for i, s in enumerate(sentences):
        candidates.append((s, [i]))
    # 2-sentence sliding windows
    for i in range(len(sentences) - 1):
        candidates.append((f"{sentences[i]} {sentences[i+1]}", [i, i+1]))

    best_score = -1.0
    best_passage = sentences[0]

    for cand_text, idxs in candidates:
        cand_lower = cand_text.lower()
        cand_tokens = set(re.findall(r"\b[a-z0-9'-]{3,}\b", cand_lower))
        overlap = substantive_claim_tokens.intersection(cand_tokens)
        overlap_count = len(overlap)

        # Base score on substantive token coverage (dominant factor)
        score = overlap_count * 4.0

        # Small density bonus
        if cand_tokens:
            density = overlap_count / len(cand_tokens)
            score += density * 1.5

        # Slight lead sentence preference if tied
        score += max(0, (3 - min(idxs)) * 0.1)

        if score > best_score:
            best_score = score
            best_passage = cand_text

    return best_passage.strip()


class WikipediaReferenceRetriever:
    """Public MediaWiki/Wikipedia general reference evidence retriever adapter.

    Retrieves authoritative encyclopedic summaries for claims using deterministic queries,
    bounded page candidates, and summary/extract endpoints without full-page crawling.
    """

    SEARCH_API_URL = "https://en.wikipedia.org/w/api.php"
    REST_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"
    USER_AGENT = "RealTimeNewsVerificationSystem/2.0 (contact: research@verification.local)"

    def __init__(
        self,
        mock_mode: bool = False,
        timeout: float = 6.0,
        max_candidates: int = 3,
        query_builder: Optional[FactCheckQueryBuilder] = None,
        mock_responses: Optional[Dict[str, Any]] = None,
        cache_max_size: int = 128,
        cache_ttl_seconds: float = 600.0
    ):
        self.mock_mode = mock_mode
        self.timeout = timeout
        self.max_candidates = max_candidates
        self.query_builder = query_builder or get_query_builder()
        self.mock_responses = mock_responses or {}
        self.api_call_count = 0
        self.cache = ReferenceCache(max_size=cache_max_size, ttl_seconds=cache_ttl_seconds)

    def _make_http_get(self, url: str) -> Dict[str, Any]:
        """Performs an HTTP GET request with standard headers, timeout, and error handling."""
        self.api_call_count += 1
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status_code = response.getcode()
                if status_code != 200:
                    raise ReferenceRetrieverAPIError(status_code, f"Received status {status_code}")
                raw_bytes = response.read()
                try:
                    return json.loads(raw_bytes.decode("utf-8"))
                except Exception as json_err:
                    raise ReferenceRetrieverMalformedResponseError(f"Malformed JSON response: {str(json_err)}")
        except urllib.error.HTTPError as http_err:
            if http_err.code == 429:
                raise ReferenceRetrieverRateLimitError(f"Rate limit exceeded (HTTP 429): {http_err.reason}")
            raise ReferenceRetrieverAPIError(http_err.code, f"HTTP Error {http_err.code}: {http_err.reason}")
        except urllib.error.URLError as url_err:
            if isinstance(url_err.reason, (TimeoutError, TimeoutError.__class__)) or "timed out" in str(url_err.reason).lower():
                raise ReferenceRetrieverTimeoutError(f"MediaWiki request timed out: {url_err.reason}")
            raise ReferenceRetrieverAPIError(0, f"Network connection error: {url_err.reason}")
        except (TimeoutError, TimeoutError.__class__):
            raise ReferenceRetrieverTimeoutError("MediaWiki request timed out.")

    def _fetch_page_summary(self, title: str) -> Optional[Dict[str, Any]]:
        """Retrieves page summary extract from MediaWiki REST API without downloading entire page."""
        if not title:
            return None

        clean_title = title.strip().replace(" ", "_")
        cache_key = f"summary:{clean_title.lower()}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        encoded_title = urllib.parse.quote(clean_title, safe="")
        summary_url = f"{self.REST_SUMMARY_URL}/{encoded_title}"

        try:
            res = self._make_http_get(summary_url)
            if res:
                self.cache.set(cache_key, res)
            return res
        except (ReferenceRetrieverAPIError, ReferenceRetrieverRateLimitError, ReferenceRetrieverTimeoutError, ReferenceRetrieverMalformedResponseError):
            return None
        except Exception:
            return None

    def search_claim_reference(
        self,
        claim: ExtractedClaim,
        max_results: Optional[int] = None
    ) -> List[EvidenceItem]:
        """Queries MediaWiki for general reference evidence items matching the claim."""
        if not claim or not claim.text:
            return []

        limit = max_results or self.max_candidates

        # 1. Deterministic Query Construction
        query = self.query_builder.build_primary_query(claim)
        if not query:
            query = claim.text.strip()

        # 2. Mock mode handling
        if self.mock_mode:
            if claim.claim_id in self.mock_responses:
                return self.mock_responses[claim.claim_id]
            if query in self.mock_responses:
                return self.mock_responses[query]
            return []

        # 3. MediaWiki Search Query Execution
        search_cache_key = f"search:{query.lower()}:{limit}"
        cached_search = self.cache.get(search_cache_key)
        if cached_search is not None:
            search_data = cached_search
        else:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": str(limit)
            }
            search_url = f"{self.SEARCH_API_URL}?{urllib.parse.urlencode(params)}"
            search_data = self._make_http_get(search_url)
            if search_data and isinstance(search_data, dict):
                self.cache.set(search_cache_key, search_data)

        if not isinstance(search_data, dict):
            raise ReferenceRetrieverMalformedResponseError("Search response must be a JSON object.")

        query_obj = search_data.get("query", {})
        search_results = query_obj.get("search", [])
        if not isinstance(search_results, list) or not search_results:
            return []

        # 4. Fetch Summary Extracts & Map to EvidenceItem Contract
        evidence_items: List[EvidenceItem] = []

        for idx, result in enumerate(search_results[:limit]):
            if not isinstance(result, dict):
                continue

            page_title = result.get("title", "").strip()
            if not page_title:
                continue

            search_snippet = strip_html_tags(result.get("snippet", ""))
            timestamp = result.get("timestamp")

            # Fetch lead summary extract
            summary_info = self._fetch_page_summary(page_title)

            extract_text = ""
            canonical_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title.replace(' ', '_'))}"

            if summary_info and isinstance(summary_info, dict):
                extract_text = summary_info.get("extract", "").strip()
                content_urls = summary_info.get("content_urls", {})
                desktop_urls = content_urls.get("desktop", {})
                if desktop_urls.get("page"):
                    canonical_url = desktop_urls["page"]
                if not timestamp and summary_info.get("timestamp"):
                    timestamp = summary_info.get("timestamp")

            # Extract focused claim-specific passage from the reference text
            final_snippet = extract_relevant_passage(
                claim=claim,
                page_title=page_title,
                full_extract=extract_text,
                search_snippet=search_snippet
            )
            if not final_snippet:
                continue

            item_id = f"ref_{claim.claim_id}_{idx + 1}"

            evidence_items.append(
                EvidenceItem(
                    id=item_id,
                    claim_id=claim.claim_id,
                    source_type=EvidenceSourceType.GENERAL_REFERENCE,
                    publisher="Wikipedia",
                    domain="en.wikipedia.org",
                    url=canonical_url,
                    title=page_title,
                    snippet=final_snippet,
                    publish_date=timestamp,
                    credibility_score=None,
                    relevance_score=None,
                    stance=StanceType.NEUTRAL,
                    raw_rating=None,
                    claim_reviewed=None
                )
            )

        return evidence_items


_reference_retriever_instance: Optional[WikipediaReferenceRetriever] = None


def get_reference_retriever(mock_mode: bool = False) -> WikipediaReferenceRetriever:
    """Returns singleton instance of WikipediaReferenceRetriever."""
    global _reference_retriever_instance
    if mock_mode:
        return WikipediaReferenceRetriever(mock_mode=True)
    if _reference_retriever_instance is None:
        _reference_retriever_instance = WikipediaReferenceRetriever(mock_mode=False)
    return _reference_retriever_instance
