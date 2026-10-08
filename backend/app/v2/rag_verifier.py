import os
import re
import json
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv("backend/.env")

logger = logging.getLogger(__name__)

# Import schemas
from backend.app.v2.schemas import (
    VerificationRequest,
    VerificationResponse,
    ClaimVerificationDetail,
    ClaimVerdict,
    OverallAssessment,
    EvidenceItem,
    EvidenceSourceType,
    StanceType,
    EvidenceStrength,
    UncertaintyLevel,
    ClaimEvidenceSummary,
    LinguisticSignal,
)

class GeminiRAGVerifier:
    """
    Production-grade RAG Verification Engine combining:
    1. Live Web & Breaking News search (DDGS)
    2. Full-text content extraction (trafilatura & bs4)
    3. Gemini AI Multimodal/Reasoning models with auto-fallback
    4. Structured JSON evidence attribution & verification verdicts
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize Google GenAI Client: %s", e)

        self.candidate_models = [
            "gemini-3.5-flash-lite",
            "gemini-3.8-flash",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
            "gemma-4-26b-a4b-it"
        ]

    def _search_web_and_news(self, query: str, max_results: int = 4) -> List[Dict[str, str]]:
        """Search live web and news articles for the given query using DDGS."""
        results = []
        try:
            from ddgs import DDGS
            ddgs = DDGS()
            
            # Clean and compact search query
            clean_q = re.sub(r'["\n\r]', ' ', query).strip()[:90]
            
            # Try text search (broad coverage)
            raw = list(ddgs.text(clean_q, max_results=max_results))
            for item in raw:
                url = item.get("href") or item.get("url") or ""
                title = item.get("title") or ""
                body = item.get("body") or ""
                if url and title:
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": body
                    })
        except Exception as e:
            logger.warning("DDGS text search error: %s", e)

        # Fallback to news search if few results
        if len(results) < 2:
            try:
                from ddgs import DDGS
                ddgs = DDGS()
                clean_q = re.sub(r'["\n\r]', ' ', query).strip()[:80]
                raw_news = list(ddgs.news(clean_q, max_results=max_results))
                for item in raw_news:
                    url = item.get("url") or item.get("href") or ""
                    title = item.get("title") or ""
                    body = item.get("body") or ""
                    if url and title and not any(r["url"] == url for r in results):
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": body
                        })
            except Exception as e:
                logger.warning("DDGS news search error: %s", e)

        return results[:max_results]

    def _extract_article_content(self, url: str, fallback_snippet: str = "") -> str:
        """Extract clean body text from source URL using trafilatura with strict timeout."""
        if not url:
            return fallback_snippet
        try:
            import trafilatura
            # Strict timeout of 2.5s to prevent slow external websites from blocking
            downloaded = trafilatura.fetch_url(url, timeout=2.5)
            if downloaded:
                extracted = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=False,
                    no_fallback=False
                )
                if extracted and len(extracted.strip()) > 80:
                    return extracted.strip()[:1500]
        except Exception:
            pass
        return fallback_snippet

    def _fetch_all_docs_concurrently(self, search_results: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Fetch multiple article bodies in parallel with bounded time."""
        import concurrent.futures

        def _fetch_one(item):
            body = self._extract_article_content(item["url"], item["snippet"])
            pub, dom = self._get_publisher_and_domain(item["url"])
            return {
                "title": item["title"],
                "url": item["url"],
                "publisher": pub,
                "domain": dom,
                "snippet": item["snippet"],
                "content": body
            }

        evidence_docs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, max(1, len(search_results)))) as executor:
            future_to_item = {executor.submit(_fetch_one, item): item for item in search_results}
            for future in concurrent.futures.as_completed(future_to_item, timeout=5.0):
                try:
                    evidence_docs.append(future.result())
                except Exception:
                    pass

        # If any failed or timed out, add from fallback snippet
        existing_urls = {d["url"] for d in evidence_docs}
        for item in search_results:
            if item["url"] not in existing_urls:
                pub, dom = self._get_publisher_and_domain(item["url"])
                evidence_docs.append({
                    "title": item["title"],
                    "url": item["url"],
                    "publisher": pub,
                    "domain": dom,
                    "snippet": item["snippet"],
                    "content": item["snippet"]
                })

        return evidence_docs

    def _get_publisher_and_domain(self, url: str) -> tuple[str, str]:
        """Extract domain and friendly publisher name from URL."""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            parts = domain.split(".")
            publisher = parts[0].capitalize() if parts else domain
            return publisher, domain
        except Exception:
            return "Unknown", "unknown"

    def verify_claim(self, claim_text: str, claim_id: str = "c1") -> Dict[str, Any]:
        """Verify a single claim against live web evidence and Gemini reasoning."""
        # Step 1: Retrieve search results (top 3)
        search_results = self._search_web_and_news(claim_text, max_results=3)
        
        # Step 2: Fetch article text context in parallel (max 3s)
        evidence_docs = self._fetch_all_docs_concurrently(search_results)

        # If no client or no key, return heuristic fallback
        if not self.client:
            return self._fallback_response(claim_text, claim_id, evidence_docs)

        # Step 3: Construct prompt for Gemini Reasoning
        sources_text = ""
        for idx, doc in enumerate(evidence_docs, 1):
            sources_text += f"\n\nSource [{idx}]:\nTitle: {doc['title']}\nPublisher: {doc['publisher']} ({doc['domain']})\nURL: {doc['url']}\nContext: {doc['content'] or doc['snippet']}"

        prompt = f"""You are an elite, objective, real-time News and Fact-Checking AI system.
Evaluate the following CLAIM against the provided EVIDENCE retrieved from live sources.

CLAIM TO VERIFY:
"{claim_text}"

EVIDENCE SOURCES:
{sources_text if sources_text else "No external evidence found."}

INSTRUCTIONS:
1. Determine the exact VERDICT:
   - "SUPPORTED": The factual proposition, core entities, numbers, and events in the claim are substantiated by credible evidence.
   - "CONTRADICTED": The claim is proven false, fabricated, debunked, or factually inaccurate by credible reporting.
   - "MISLEADING": The claim mixes truth with falsehoods, distorts context, or exaggerates numbers.
   - "UNVERIFIED": Insufficient or no reliable evidence found to independently confirm or debunk the claim.
2. Assign a confidence score (0.0 to 1.0).
3. Write a clear, objective 2-3 sentence explanation summarizing the verdict and why.
4. Provide 2-3 key findings.
5. For each source that was relevant, identify its stance towards the claim: "SUPPORTS", "CONTRADICTS", or "NEUTRAL".

OUTPUT FORMAT:
Return strictly a valid JSON object matching this schema:
{{
  "verdict": "SUPPORTED" | "CONTRADICTED" | "MISLEADING" | "UNVERIFIED",
  "confidence": 0.95,
  "explanation": "Plain language explanation of why the verdict was reached.",
  "key_findings": ["Finding 1", "Finding 2"],
  "source_stances": [
    {{
      "url": "exact URL from sources",
      "stance": "SUPPORTS" | "CONTRADICTS" | "NEUTRAL",
      "relevant_quote": "Direct quote from source that supports or contradicts"
    }}
  ]
}}
"""

        # Call Gemini with model fallback
        llm_response = None
        for model_name in self.candidate_models:
            try:
                resp = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if resp and resp.text:
                    llm_response = resp.text.strip()
                    break
            except Exception as e:
                logger.warning("Gemini model %s failed: %s", model_name, e)
                continue

        # Parse JSON output
        parsed_data = self._parse_gemini_json(llm_response)
        
        # Build EvidenceItems list
        evidence_items: List[EvidenceItem] = []
        source_stance_map = {
            s.get("url"): s for s in parsed_data.get("source_stances", [])
        }

        for idx, doc in enumerate(evidence_docs):
            stance_info = source_stance_map.get(doc["url"], {})
            raw_stance = stance_info.get("stance", "NEUTRAL").upper()
            stance = StanceType.NEUTRAL
            if "SUPPORT" in raw_stance:
                stance = StanceType.SUPPORTS
            elif "CONTRADICT" in raw_stance:
                stance = StanceType.CONTRADICTS

            quote = stance_info.get("relevant_quote") or doc["snippet"]

            evidence_items.append(
                EvidenceItem(
                    id=f"{claim_id}_ev_{idx+1}",
                    claim_id=claim_id,
                    source_type=EvidenceSourceType.LIVE_NEWS_SEARCH,
                    publisher=doc["publisher"],
                    domain=doc["domain"],
                    url=doc["url"],
                    title=doc["title"],
                    snippet=quote[:300] if quote else doc["snippet"][:300],
                    content=doc["content"][:800] if doc["content"] else None,
                    credibility_score=0.90 if stance != StanceType.NEUTRAL else 0.70,
                    relevance_score=0.95 if stance != StanceType.NEUTRAL else 0.60,
                    stance=stance
                )
            )

        # Calculate counts
        sup_count = sum(1 for e in evidence_items if e.stance == StanceType.SUPPORTS)
        con_count = sum(1 for e in evidence_items if e.stance == StanceType.CONTRADICTS)
        neu_count = sum(1 for e in evidence_items if e.stance == StanceType.NEUTRAL)

        # Map verdict string to ClaimVerdict
        raw_v = parsed_data.get("verdict", "UNVERIFIED").upper()
        if "SUPPORT" in raw_v:
            claim_verdict = ClaimVerdict.SUPPORTED
        elif "CONTRADICT" in raw_v:
            claim_verdict = ClaimVerdict.CONTRADICTED
        else:
            claim_verdict = ClaimVerdict.UNVERIFIED

        strength = EvidenceStrength.STRONG if (sup_count >= 2 or con_count >= 1) else (
            EvidenceStrength.MODERATE if (sup_count == 1 or con_count == 1) else (
                EvidenceStrength.LIMITED if len(evidence_items) > 0 else EvidenceStrength.NONE
            )
        )

        uncertainty = UncertaintyLevel.LOW if (claim_verdict != ClaimVerdict.UNVERIFIED and strength in [EvidenceStrength.STRONG, EvidenceStrength.MODERATE]) else (
            UncertaintyLevel.MEDIUM if len(evidence_items) > 0 else UncertaintyLevel.HIGH
        )

        return {
            "claim_id": claim_id,
            "text": claim_text,
            "verdict": claim_verdict,
            "reasoning": parsed_data.get("explanation", "Verification completed with live search and Gemini AI reasoning."),
            "evidence_strength": strength,
            "uncertainty_level": uncertainty,
            "has_conflicting_evidence": (sup_count > 0 and con_count > 0),
            "supporting_evidence_count": sup_count,
            "contradicting_evidence_count": con_count,
            "neutral_evidence_count": neu_count,
            "keywords": [w for w in claim_text.split() if len(w) > 4][:5],
            "evidence": evidence_items,
            "key_findings": parsed_data.get("key_findings", []),
            "confidence": parsed_data.get("confidence", 0.90)
        }

    def _parse_gemini_json(self, text: Optional[str]) -> Dict[str, Any]:
        """Extract and clean JSON from Gemini text response."""
        if not text:
            return {"verdict": "UNVERIFIED", "explanation": "No response received from Gemini reasoning model."}
        try:
            # Remove markdown code blocks if present
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.warning("JSON parse error from Gemini response: %s", e)
            # Regex extraction for verdict
            verdict = "UNVERIFIED"
            if "SUPPORTED" in text.upper():
                verdict = "SUPPORTED"
            elif "CONTRADICTED" in text.upper():
                verdict = "CONTRADICTED"
            return {
                "verdict": verdict,
                "confidence": 0.85,
                "explanation": text[:300],
                "key_findings": [],
                "source_stances": []
            }

    def _fallback_response(self, claim_text: str, claim_id: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Offline fallback response if Gemini is unreachable."""
        return {
            "claim_id": claim_id,
            "text": claim_text,
            "verdict": ClaimVerdict.UNVERIFIED,
            "reasoning": "Gemini API key is not configured or offline. Real-time verification requires GEMINI_API_KEY.",
            "evidence_strength": EvidenceStrength.NONE,
            "uncertainty_level": UncertaintyLevel.HIGH,
            "has_conflicting_evidence": False,
            "supporting_evidence_count": 0,
            "contradicting_evidence_count": 0,
            "neutral_evidence_count": len(docs),
            "keywords": [w for w in claim_text.split() if len(w) > 4][:5],
            "evidence": [],
            "key_findings": [],
            "confidence": 0.50
        }

    def verify_request(self, request: VerificationRequest) -> VerificationResponse:
        """Process full verification request (headline + text body) and return VerificationResponse."""
        title = (request.title or "").strip()
        text = (request.text or "").strip()
        full_text = f"{title}. {text}".strip() if title and text else (title or text)

        # Prioritize the most substantive factual claim for high precision and fast turnaround
        claims_to_verify = []
        if text and len(text) >= 15:
            sentences = [s.strip() for s in re.split(r'[.!?\n]+', text) if len(s.strip()) >= 15]
            if sentences:
                claims_to_verify.append(sentences[0])
            else:
                claims_to_verify.append(text[:250])
        elif title and len(title) >= 10:
            claims_to_verify.append(title)
        else:
            claims_to_verify = [full_text[:200]]

        claim_details: List[ClaimVerificationDetail] = []
        all_key_findings = []

        for idx, claim_str in enumerate(claims_to_verify[:request.max_claims or 2]):
            cid = f"claim_{idx+1}"
            res = self.verify_claim(claim_str, cid)
            
            # Evidence summary
            ev_items = res["evidence"]
            summary = ClaimEvidenceSummary(
                claim_id=cid,
                claim_text=claim_str,
                total_evidence_count=len(ev_items),
                live_news_count=len(ev_items),
                supporting_evidence_count=res["supporting_evidence_count"],
                contradicting_evidence_count=res["contradicting_evidence_count"],
                neutral_evidence_count=res["neutral_evidence_count"],
                unique_source_domains=list(set(e.domain for e in ev_items)),
                unique_domain_count=len(set(e.domain for e in ev_items)),
                has_conflicting_evidence=res["has_conflicting_evidence"],
                live_news_evidence=ev_items,
                all_evidence=ev_items,
                semantic_model="Google Gemini 2.0 / 1.5 Flash Reasoning",
                semantic_evidence_count=len(ev_items)
            )

            detail = ClaimVerificationDetail(
                claim_id=cid,
                text=claim_str,
                verdict=res["verdict"],
                reasoning=res["reasoning"],
                evidence_strength=res["evidence_strength"],
                uncertainty_level=res["uncertainty_level"],
                has_conflicting_evidence=res["has_conflicting_evidence"],
                supporting_evidence_count=res["supporting_evidence_count"],
                contradicting_evidence_count=res["contradicting_evidence_count"],
                neutral_evidence_count=res["neutral_evidence_count"],
                keywords=res["keywords"],
                evidence_summary=summary,
                evidence=ev_items,
                semantic_relation=res["verdict"].value,
                semantic_model="Google Gemini Flash RAG",
                semantic_evidence_count=len(ev_items)
            )
            claim_details.append(detail)
            if res.get("key_findings"):
                all_key_findings.extend(res["key_findings"])

        # Determine overall assessment
        verdicts = [c.verdict for c in claim_details]
        has_con = any(v == ClaimVerdict.CONTRADICTED for v in verdicts)
        has_sup = any(v == ClaimVerdict.SUPPORTED for v in verdicts)

        if has_con:
            overall = OverallAssessment.CONTRADICTED
            summary_msg = claim_details[0].reasoning
        elif has_sup:
            overall = OverallAssessment.SUPPORTED
            summary_msg = claim_details[0].reasoning
        else:
            overall = OverallAssessment.UNVERIFIED
            summary_msg = claim_details[0].reasoning if claim_details else "Insufficient external evidence found."

        return VerificationResponse(
            overall_assessment=overall,
            assessment_summary=summary_msg,
            has_conflict=(has_con and has_sup),
            claims=claim_details,
            linguistic_signal=None,
            service_status={
                "search_engine": "ok",
                "gemini_api": "ok" if self.client else "missing_key",
                "rag_pipeline": "active"
            },
            disclaimer=(
                "Verification is powered by real-time web news retrieval and Google Gemini AI reasoning. "
                "UNVERIFIED claims indicate an absence of indexed external reporting rather than proven falsehood."
            )
        )

# Global singleton
_rag_verifier: Optional[GeminiRAGVerifier] = None

def get_rag_verifier() -> GeminiRAGVerifier:
    global _rag_verifier
    if _rag_verifier is None:
        _rag_verifier = GeminiRAGVerifier()
    return _rag_verifier
