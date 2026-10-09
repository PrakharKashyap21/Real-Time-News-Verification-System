from typing import Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from backend.app.v2.schemas import (
    VerificationRequest,
    VerificationResponse,
    URLExtractRequest,
    URLExtractResponse,
    DocumentAuditRequest,
    DocumentAuditResponse,
    AnalyticsResponse,
    RadarResponse,
)
from backend.app.v2.verification_service import get_verification_service, VerificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["V2 Verification"])



@router.post("/extract-url", response_model=URLExtractResponse)
def extract_url_content(payload: URLExtractRequest):
    url = (payload.url or "").strip()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid URL is required."
        )
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc or ""

    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url, timeout=6.0)
        title = ""
        text = ""
        author = None
        
        if downloaded:
            extracted_text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                no_fallback=False
            )
            meta = trafilatura.extract_metadata(downloaded)
            if meta:
                title = meta.title or ""
                author = meta.author or None
            if extracted_text:
                text = extracted_text.strip()
        
        if not text:
            # Fallback using urllib and BeautifulSoup
            import urllib.request
            from bs4 import BeautifulSoup
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                if not title:
                    og_title = soup.find("meta", property="og:title")
                    if og_title and og_title.get("content"):
                        title = og_title["content"].strip()
                    elif soup.title and soup.title.string:
                        title = soup.title.string.strip()
                
                paras = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 30]
                text = "\n\n".join(paras[:15])

        if not text and not title:
            return URLExtractResponse(
                url=url,
                domain=domain,
                success=False,
                error="Could not extract readable article text from this URL."
            )

        return URLExtractResponse(
            url=url,
            title=title or "",
            text=text or "",
            domain=domain,
            author=author,
            success=True
        )
    except Exception as e:
        logger.warning("URL extraction failed for %s: %s", url, e)
        return URLExtractResponse(
            url=url,
            domain=domain,
            success=False,
            error=f"Failed to fetch content from URL: {str(e)}"
        )


@router.post("/verify", response_model=VerificationResponse)
def verify_news_v2(payload: VerificationRequest, service: VerificationService = Depends(get_verification_service)):
    try:
        from backend.app.main import app
        # If in mock_mode or overridden in tests, use the mock/baseline service
        is_mocked = getattr(service, "mock_mode", False) or (get_verification_service in getattr(app, "dependency_overrides", {}))
        
        if not is_mocked:
            from backend.app.v2.rag_verifier import get_rag_verifier
            rag_verifier = get_rag_verifier()
            if rag_verifier.client:
                try:
                    rag_res = rag_verifier.verify_request(payload)
                    if payload.include_linguistic_signal and not rag_res.linguistic_signal:
                        try:
                            rag_res.linguistic_signal = service.svm_provider.get_signal(
                                title=payload.title or "",
                                text=payload.text or ""
                            )
                        except Exception:
                            pass
                    return rag_res
                except Exception as e:
                    logger.warning("RAG verifier exception, falling back to baseline service: %s", e)

        return service.verify_news(payload)

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error("V2 verification service error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The verification service encountered an internal error. Please try again later."
        )


@router.post("/audit-document", response_model=DocumentAuditResponse)
def audit_document_content(payload: DocumentAuditRequest):
    content = (payload.content or "").strip()
    if not content or len(content) < 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document content is too brief for fact-checking audit. Please provide at least 30 characters."
        )

    from backend.app.v2.rag_verifier import get_rag_verifier
    rag = get_rag_verifier()
    return rag.audit_document(
        content=content,
        title=payload.title,
        filename=payload.filename
    )


@router.post("/audit-file", response_model=DocumentAuditResponse)
async def audit_uploaded_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No file uploaded."
        )

    allowed_exts = (".pdf", ".txt", ".md")
    if not any(file.filename.lower().endswith(ext) for ext in allowed_exts):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported file format. Please upload a PDF (.pdf) or text document (.txt, .md)."
        )

    try:
        file_bytes = await file.read()
        from backend.app.v2.document_parser import extract_text_from_file_bytes
        inferred_title, extracted_text = extract_text_from_file_bytes(file_bytes, file.filename)

        if len(extracted_text) < 30:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Extracted text is too brief to conduct an authenticity audit."
            )

        from backend.app.v2.rag_verifier import get_rag_verifier
        rag = get_rag_verifier()
        return rag.audit_document(
            content=extracted_text,
            title=inferred_title,
            filename=file.filename
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error("File audit error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to audit document: {str(e)}"
        )


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(domain: Optional[str] = None):
    from backend.app.v2.analytics_service import get_analytics_summary
    return get_analytics_summary(query_domain=domain)


@router.get("/radar", response_model=RadarResponse)
def get_radar(category: Optional[str] = None):
    from backend.app.v2.radar_service import fetch_radar_feed
    return fetch_radar_feed(category=category)


