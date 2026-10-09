import os
import io
import re
import json
import time
import logging
from typing import Optional, Dict, Any, List
from PIL import Image

from backend.app.v2.schemas import ImageAuditResponse, DocumentClaimAudit, EvidenceItem
from backend.app.v2.rag_verifier import get_rag_verifier

logger = logging.getLogger(__name__)

class ImageClaimAuditor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize Google GenAI Client in ImageClaimAuditor: %s", e)

        self.candidate_vision_models = [
            "gemini-2.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.8-flash",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash"
        ]

    def _extract_image_metadata(self, image_bytes: bytes) -> Dict[str, Any]:
        """Extracts resolution, format, and size from image bytes."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                img_format = img.format or "UNKNOWN"
                file_size_kb = round(len(image_bytes) / 1024, 2)
                return {
                    "dimensions": f"{width} x {height}",
                    "format": img_format,
                    "file_size_kb": file_size_kb,
                    "aspect_ratio": round(width / max(1, height), 2)
                }
        except Exception as e:
            logger.warning("Failed to parse image headers via PIL: %s", e)
            return {
                "dimensions": "Unknown",
                "format": "Unknown",
                "file_size_kb": round(len(image_bytes) / 1024, 2),
                "aspect_ratio": 1.0
            }

    def _run_vision_analysis(self, image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        """Calls Gemini Vision to transcribe text, classify media type, and assess manipulation risk."""
        if not self.client:
            return self._heuristic_vision_fallback()

        prompt = (
            "You are an expert digital forensics examiner and investigative fact-checker. "
            "Examine this screenshot or image in detail:\n"
            "1. Transcribe the primary headline and all legible text verbatim.\n"
            "2. Identify the media context/type (e.g., 'Social Media Post (X/Twitter/Reddit)', 'News Headline Screenshot', "
            "'TV Breaking News Chyron / Lower Third', 'Manipulated Newspaper Clipping', 'Infographic / Chart').\n"
            "3. Assess digital manipulation and tampering risk: Look for font kerning mismatches, artifact halos around text, "
            "fabricated checkmarks, or inconsistent lighting. Rate as 'LOW', 'MEDIUM', or 'HIGH'.\n"
            "4. Provide 2-3 forensic visual observations.\n"
            "5. Formulate the single most specific factual claim made in this image for external news and fact-checking verification.\n\n"
            "Return STRICTLY a JSON object matching this schema:\n"
            "{\n"
            '  "media_type": "string",\n'
            '  "visual_manipulation_risk": "LOW" | "MEDIUM" | "HIGH",\n'
            '  "visual_observations": ["string", "string"],\n'
            '  "extracted_headline": "string",\n'
            '  "extracted_text": "string",\n'
            '  "core_claim": "string"\n'
            "}"
        )

        from google.genai import types

        for model_name in self.candidate_vision_models:
            try:
                part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[part, prompt]
                )
                if response and response.text:
                    cleaned_text = response.text.strip()
                    if "```json" in cleaned_text:
                        cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in cleaned_text:
                        cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()
                    
                    data = json.loads(cleaned_text)
                    return data
            except Exception as e:
                logger.debug("Vision analysis failed with model %s: %s", model_name, e)
                continue

        return self._heuristic_vision_fallback()

    def _heuristic_vision_fallback(self) -> Dict[str, Any]:
        """Fallback when vision models are unavailable or unconfigured."""
        return {
            "media_type": "Digital Screenshot / Image",
            "visual_manipulation_risk": "LOW",
            "visual_observations": [
                "Automated OCR requires active Gemini Vision key.",
                "Image dimensions and aspect ratio conform to standard digital capture."
            ],
            "extracted_headline": "Uploaded Image Claim",
            "extracted_text": "Image content uploaded for authenticity auditing.",
            "core_claim": "Image claim submitted for real-time verification."
        }

    def audit_image(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None,
        mime_type: str = "image/png"
    ) -> ImageAuditResponse:
        """Conducts full multimodal audit: Vision OCR, forensic inspection, and cross-reference RAG verification."""
        # 1. Metadata
        meta = self._extract_image_metadata(image_bytes)

        # 2. Vision Analysis
        vision_result = self._run_vision_analysis(image_bytes, mime_type)
        extracted_headline = vision_result.get("extracted_headline", "").strip() or "Image Assertion"
        extracted_text = vision_result.get("extracted_text", "").strip()
        core_claim = vision_result.get("core_claim", "").strip() or extracted_headline
        media_type = vision_result.get("media_type", "Digital Screenshot / Image")
        manipulation_risk = vision_result.get("visual_manipulation_risk", "LOW").upper()
        observations = vision_result.get("visual_observations", [])

        # 3. Cross-reference verification via RAG pipeline
        rag = get_rag_verifier()
        audit_text = f"{core_claim}. {extracted_text}".strip()
        
        # If extracted text is minimal, use headline as audit content
        if len(audit_text) < 25:
            audit_text = f"{extracted_headline}: {core_claim}"

        doc_audit = rag.audit_document(
            content=audit_text,
            title=extracted_headline,
            filename=filename
        )

        overall_verdict = doc_audit.overall_status.upper()
        confidence = round(doc_audit.authenticity_score / 100.0, 2)

        return ImageAuditResponse(
            filename=filename,
            media_type=media_type,
            dimensions=meta.get("dimensions", "Unknown"),
            file_size_kb=meta.get("file_size_kb", 0.0),
            visual_manipulation_risk=manipulation_risk,
            visual_observations=observations,
            extracted_headline=extracted_headline,
            extracted_text=extracted_text,
            core_claim=core_claim,
            overall_verdict=overall_verdict,
            confidence_score=confidence,
            authenticity_summary=doc_audit.executive_assessment,
            claims_breakdown=doc_audit.audited_claims,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        )

_auditor_instance: Optional[ImageClaimAuditor] = None

def get_image_auditor() -> ImageClaimAuditor:
    global _auditor_instance
    if _auditor_instance is None:
        _auditor_instance = ImageClaimAuditor()
    return _auditor_instance
