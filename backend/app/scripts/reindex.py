"""Rebuild the ChromaDB index from the canonical chunks stored in the relational database.

Use after Chroma storage was lost (ephemeral hosting disk) or after changing the embedding model:
    python -m app.scripts.reindex            # add missing vectors
    python -m app.scripts.reindex --full     # wipe and re-embed everything"""
from __future__ import annotations

import argparse
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document, DocumentStatus
from app.services.embeddings import Embedder
from app.services.vectorstore import VectorStore

log = logging.getLogger("campusvoice.reindex")


def processed_chunk_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Chunk).join(Document).where(Document.processing_status == DocumentStatus.processed.value)) or 0


def reindex(db: Session, embedder: Embedder, vectors: VectorStore, full: bool = False, batch: int = 64) -> int:
    rows = db.execute(select(Chunk, Document).join(Document).where(Document.processing_status == DocumentStatus.processed.value)
                      .order_by(Document.id, Chunk.chunk_index)).all()
    if full:
        for doc_id in {d.id for _, d in rows}:
            vectors.delete_document(doc_id)
    existing = set() if full else set(vectors._col.get(include=[])["ids"])
    todo = [(c, d) for c, d in rows if c.id not in existing]
    for i in range(0, len(todo), batch):
        part = todo[i : i + batch]
        vecs = embedder.embed_passages([c.content for c, _ in part])
        vectors.upsert([c.id for c, _ in part], vecs, [c.content for c, _ in part],
                       [{"document_id": d.id, "title": d.title, "department": d.department, "category": d.category,
                         "source_date": d.source_date.isoformat(), "page_number": c.page_number, "chunk_index": c.chunk_index} for c, d in part])
        for c, _ in part:
            c.vector_id = c.id
    db.commit()
    return len(todo)


def main() -> None:
    from app.db.session import get_sessionmaker
    from app.services.embeddings import get_embedder
    from app.services.vectorstore import get_vectorstore

    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    with get_sessionmaker()() as db:
        n = reindex(db, get_embedder(), get_vectorstore(), full=ap.parse_args().full)
    print(f"Indexed {n} chunk(s).")


if __name__ == "__main__":
    main()
