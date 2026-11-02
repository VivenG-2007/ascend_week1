"""Public access to the ORIGINAL file behind a source chip. Only processed (official) documents are served."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentStatus
from app.db.session import get_db
from app.services.storage import get_storage

router = APIRouter(prefix="/api/documents", tags=["documents"])
log = logging.getLogger("campusvoice.documents")


@router.get("/{doc_id}/file")
def document_file(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None or doc.processing_status != DocumentStatus.processed.value or not doc.storage_path:
        raise HTTPException(404, "Document not found.")
    storage = get_storage()
    try:
        url = storage.public_url(doc.storage_path)
        if url:
            return RedirectResponse(url)
        return Response(storage.read(doc.storage_path), media_type=doc.mime_type or "application/octet-stream",
                        headers={"Content-Disposition": f'inline; filename="{doc.original_filename or "document"}"',
                                 "X-Content-Type-Options": "nosniff"})
    except Exception:  # noqa: BLE001
        log.exception("Could not serve document")
        raise HTTPException(404, "Document file is unavailable.")
