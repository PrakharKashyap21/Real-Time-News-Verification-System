import logging
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.v2.schemas import VerificationRequest, VerificationResponse
from backend.app.v2.verification_service import get_verification_service, VerificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["V2 Verification"])


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
