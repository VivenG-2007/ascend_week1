"""
Document Extraction & OCR Service
Supports native PDF extraction, Azure AI Document Intelligence, and GPT-4.1 Vision fallback.
"""
import io
import logging
from typing import List, Dict, Any, Tuple, Optional
from app.config import settings

logger = logging.getLogger("campusvoice.ocr")

def extract_text_from_pdf_stream(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts text page-by-page from PDF bytes.
    Returns a list of dicts: {"page_number": int, "text": str, "ocr_applied": bool, "warnings": str}
    """
    pages_data = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        
        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            extracted = page.extract_text() or ""
            extracted = extracted.strip()

            ocr_applied = False
            warning = None

            # If extractable text is very sparse (< 40 characters), attempt OCR
            if len(extracted) < 40:
                logger.info(f"[OCR] Page {page_num} has sparse text ({len(extracted)} chars). Triggering OCR fallback...")
                ocr_text, warning = perform_cloud_ocr_or_vision(file_bytes, is_pdf=True, page_num=page_num)
                if ocr_text:
                    extracted = ocr_text
                    ocr_applied = True

            pages_data.append({
                "page_number": page_num,
                "text": extracted,
                "ocr_applied": ocr_applied,
                "warnings": warning
            })
    except Exception as e:
        logger.error(f"[EXTRACTION ERROR] Failed to parse PDF: {e}")
        pages_data.append({
            "page_number": 1,
            "text": "",
            "ocr_applied": False,
            "warnings": f"Extraction failure: {str(e)}"
        })

    return pages_data

def extract_text_from_image_stream(file_bytes: bytes, mime_type: str = "image/png") -> Dict[str, Any]:
    """
    Extracts text from image bytes using Azure Document Intelligence or GPT-4.1 Vision.
    """
    ocr_text, warning = perform_cloud_ocr_or_vision(file_bytes, is_pdf=False, mime_type=mime_type)
    return {
        "page_number": 1,
        "text": ocr_text or "",
        "ocr_applied": True,
        "warnings": warning
    }

def perform_cloud_ocr_or_vision(
    file_bytes: bytes, 
    is_pdf: bool = False, 
    page_num: int = 1,
    mime_type: str = "application/pdf"
) -> Tuple[str, Optional[str]]:
    """
    Attempts Azure AI Document Intelligence first; if not configured, uses GPT-4.1 Vision;
    otherwise logs warning for admin review.
    """
    # 1. Try Azure AI Document Intelligence
    if settings.AZURE_DOC_INTEL_ENDPOINT and settings.AZURE_DOC_INTEL_KEY:
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

            client = DocumentIntelligenceClient(
                endpoint=settings.AZURE_DOC_INTEL_ENDPOINT,
                credential=AzureKeyCredential(settings.AZURE_DOC_INTEL_KEY)
            )
            poller = client.begin_analyze_document(
                "prebuilt-layout",
                AnalyzeDocumentRequest(bytes_source=file_bytes)
            )
            result = poller.result()
            lines = [line.content for page in result.pages for line in page.lines]
            return "\n".join(lines), None
        except Exception as e:
            logger.warning(f"[OCR] Azure Document Intelligence failed: {e}")

    # 2. Try GPT-4.1 Vision via Azure AI Foundry / OpenAI
    if settings.AZURE_AI_FOUNDRY_ENDPOINT and settings.AZURE_AI_FOUNDRY_API_KEY:
        try:
            import base64
            from openai import AzureOpenAI
            b64_image = base64.b64encode(file_bytes).decode("utf-8")
            
            client = AzureOpenAI(
                azure_endpoint=settings.AZURE_AI_FOUNDRY_ENDPOINT,
                api_key=settings.AZURE_AI_FOUNDRY_API_KEY,
                api_version=settings.AZURE_AI_FOUNDRY_API_VERSION
            )
            response = client.chat.completions.create(
                model=settings.MODEL_VISION,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text, notices, dates, tables, and official circular content from this document image accurately. Do not summarize; transcribe the exact text verbatim in English and Telugu."},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_image}"}}
                        ]
                    }
                ],
                max_tokens=2000
            )
            return response.choices[0].message.content, None
        except Exception as e:
            logger.warning(f"[OCR] Vision model OCR failed: {e}")

    return "", "Cloud OCR credentials (AZURE_DOC_INTEL or AZURE_AI_FOUNDRY) not configured. Uploaded scan requires OCR provider."
