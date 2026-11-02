"""OCR via Azure AI Document Intelligence (Form Recognizer prebuilt-read model).

Falls back to NullOcr when OCR_PROVIDER=none or Azure credentials are missing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

from app.config import get_settings

log = logging.getLogger("campusvoice.ocr")


class OcrUnavailable(RuntimeError):
    pass


@dataclass
class OcrResult:
    text: str
    confidence: float | None = None
    warnings: list[str] = field(default_factory=list)


class OcrProvider(Protocol):
    name: str

    def ocr_image(self, png_bytes: bytes) -> OcrResult: ...


class NullOcr:
    name = "none"

    def ocr_image(self, png_bytes: bytes) -> OcrResult:
        raise OcrUnavailable("OCR is disabled (OCR_PROVIDER=none).")


class AzureDocumentIntelligenceOcr:
    """OCR via Azure AI Document Intelligence (prebuilt-read model).

    Requires:
      AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = https://<resource>.cognitiveservices.azure.com/
      AZURE_DOCUMENT_INTELLIGENCE_KEY      = <32-byte key>

    Install: pip install azure-ai-documentintelligence
    """

    name = "azure-document-intelligence"
    MAX_IMAGE_BYTES = 4 * 1024 * 1024  # Azure Document Intelligence Free tier limit is 4MB

    def __init__(self, endpoint: str, key: str) -> None:
        log.info("Initialising Azure Document Intelligence OCR endpoint=%s", endpoint)
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError as exc:
            raise OcrUnavailable(
                "azure-ai-documentintelligence is not installed. "
                "Run: pip install azure-ai-documentintelligence"
            ) from exc
        self._client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))
        log.info("Azure Document Intelligence OCR ready")

    @classmethod
    def _optimize_image(cls, data: bytes) -> bytes:
        """Compress or downscale images exceeding Azure Document Intelligence's payload limit using PyMuPDF."""
        if len(data) <= cls.MAX_IMAGE_BYTES:
            return data

        import pymupdf as fitz

        log.info(
            "Image size (%d bytes) exceeds Azure OCR limit (%d bytes); compressing...",
            len(data),
            cls.MAX_IMAGE_BYTES,
        )
        try:
            pix = fitz.Pixmap(data)
            if pix.alpha:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            for quality in (85, 70, 55, 40):
                compressed = pix.tobytes("jpeg", jpg_quality=quality)
                if len(compressed) <= cls.MAX_IMAGE_BYTES:
                    log.info(
                        "Compressed image: %d -> %d bytes (quality=%d)",
                        len(data),
                        len(compressed),
                        quality,
                    )
                    return compressed
            return compressed
        except Exception:
            log.exception("Image compression failed; falling back to original data")
            return data

    def ocr_image(self, png_bytes: bytes) -> OcrResult:
        payload = self._optimize_image(png_bytes)
        log.debug("Azure Document Intelligence: sending %d bytes for OCR", len(payload))
        try:
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

            poller = self._client.begin_analyze_document(
                "prebuilt-read",
                AnalyzeDocumentRequest(bytes_source=payload),
            )
            result = poller.result()
        except Exception as exc:  # noqa: BLE001
            log.exception("Azure Document Intelligence OCR failed")
            raise OcrUnavailable(f"Azure Document Intelligence failed: {exc}") from exc

        lines: list[str] = []
        confidences: list[float] = []
        for page in result.pages or []:
            for line in page.lines or []:
                lines.append(line.content)
            for word in page.words or []:
                if word.confidence is not None:
                    confidences.append(float(word.confidence))

        text = "\n".join(lines)
        avg_conf = (sum(confidences) / len(confidences)) if confidences else None
        warnings: list[str] = []

        if not text.strip():
            warnings.append("Azure Document Intelligence found no readable text.")
        elif avg_conf is not None and avg_conf < 0.55:
            warnings.append(
                f"Low OCR confidence ({avg_conf:.0%}); text may contain errors."
            )

        log.debug(
            "Azure OCR complete: %d chars across %d lines, avg_confidence=%.3f",
            len(text),
            len(lines),
            avg_conf or 0.0,
        )
        return OcrResult(text=text, confidence=avg_conf, warnings=warnings)


@lru_cache
def get_ocr() -> OcrProvider:
    s = get_settings()
    if s.ocr_provider == "none":
        log.info("OCR disabled (OCR_PROVIDER=none)")
        return NullOcr()
    if s.ocr_provider == "azure":
        if not s.azure_ocr_configured:
            log.warning(
                "OCR_PROVIDER=azure but AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT/KEY not set — OCR disabled"
            )
            return NullOcr()
        try:
            return AzureDocumentIntelligenceOcr(
                s.azure_document_intelligence_endpoint,  # type: ignore[arg-type]
                s.azure_document_intelligence_key,       # type: ignore[arg-type]
            )
        except OcrUnavailable as exc:
            log.warning("Azure OCR unavailable: %s — OCR disabled", exc)
            return NullOcr()
    log.warning("Unknown OCR_PROVIDER=%r — OCR disabled", s.ocr_provider)
    return NullOcr()
