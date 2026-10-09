import io
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

def extract_text_from_file_bytes(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Extracts text content and inferred title from raw file bytes.
    Supports PDF (.pdf) and Plain Text (.txt, .md).
    Returns (inferred_title, extracted_text).
    """
    fname = filename.lower()
    inferred_title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    text = ""

    if fname.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            parts = []
            for i, page in enumerate(reader.pages[:20]):
                p_text = page.extract_text()
                if p_text:
                    parts.append(p_text.strip())
            text = "\n\n".join(parts).strip()
            
            # Check metadata for title
            if reader.metadata and reader.metadata.title:
                inferred_title = reader.metadata.title.strip()
        except Exception as e:
            logger.warning("PDF extraction failed for %s: %s", filename, e)
            raise ValueError(f"Failed to read PDF file: {str(e)}")

    else:
        # Assume text / markdown
        try:
            text = file_bytes.decode("utf-8", errors="ignore").strip()
        except Exception as e:
            logger.warning("Text decoding failed for %s: %s", filename, e)
            raise ValueError(f"Failed to read text file: {str(e)}")

    if not text:
        raise ValueError("The uploaded document contains no readable text content.")

    return inferred_title, text
