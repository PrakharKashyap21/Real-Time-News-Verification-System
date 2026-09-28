import os
import re
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Optional, Dict, Any
from backend.app.v2.schemas import (
    EvidenceItem,
    ExtractedClaim,
    EvidenceSourceType,
    StanceType
)
from backend.app.v2.query_builder import get_query_builder, FactCheckQueryBuilder


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
        mock_responses: Optional[Dict[str, Any]] = None
    ):
        self.mock_mode = mock_mode
        self.timeout = timeout
        self.max_candidates = max_candidates
        self.query_builder = query_builder or get_query_builder()
        self.mock_responses = mock_responses or {}
        self.api_call_count = 0

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
        encoded_title = urllib.parse.quote(clean_title, safe="")
        summary_url = f"{self.REST_SUMMARY_URL}/{encoded_title}"

        try:
            return self._make_http_get(summary_url)
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
            # Default deterministic mock responses if mock mode is on
            return []

        # 3. MediaWiki Search Query Execution
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": str(limit)
        }
        search_url = f"{self.SEARCH_API_URL}?{urllib.parse.urlencode(params)}"

        search_data = self._make_http_get(search_url)

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

            # Fallback to search snippet if extract is empty
            final_snippet = extract_text if extract_text else search_snippet
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
    if _reference_retriever_instance is None or mock_mode:
        _reference_retriever_instance = WikipediaReferenceRetriever(mock_mode=mock_mode)
    return _reference_retriever_instance
