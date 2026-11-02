"""Retrieval service: query normalisation, vector search, dedupe, supersession, metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document, DocumentStatus
from app.schemas.chat import RetrievalMetrics, SourceRef
from app.services.embeddings import Embedder
from app.services.text_clean import normalize_query
from app.services.vectorstore import VectorStore


@dataclass
class Hit:
    chunk_id: str
    document_id: str
    title: str
    department: str
    source_date: date | None
    page_number: int
    chunk_index: int
    score: float  # cosine similarity (1 - cosine distance); higher is better
    distance: float
    content: str
    superseded_note: str | None = None

    def to_source(self) -> SourceRef:
        return SourceRef(document_id=self.document_id, title=self.title, source_date=self.source_date,
                         page_number=self.page_number, department=self.department, score=round(self.score, 4),
                         superseded_note=self.superseded_note)


@dataclass
class RetrievalResult:
    hits: list[Hit] = field(default_factory=list)
    metrics: RetrievalMetrics = field(default_factory=RetrievalMetrics)


class RetrievalService:
    def __init__(self, db: Session, embedder: Embedder, vectors: VectorStore, threshold: float) -> None:
        self.db, self.embedder, self.vectors, self.threshold = db, embedder, vectors, threshold

    # -- helpers
    def _newest_replacement(self, doc_id: str) -> Document | None:
        """Follow supersedes links forward to the newest processed document."""
        current, seen = None, {doc_id}
        nxt = doc_id
        while True:
            rep = self.db.scalar(
                select(Document).where(Document.supersedes_id == nxt, Document.processing_status == DocumentStatus.processed.value)
            )
            if rep is None or rep.id in seen:
                return current
            current, nxt = rep, rep.id
            seen.add(rep.id)

    def _to_hits(self, raw) -> list[Hit]:
        ids = [h.chunk_id for h in raw]
        rows = {c.id: c for c in self.db.scalars(select(Chunk).where(Chunk.id.in_(ids)))} if ids else {}
        out: list[Hit] = []
        for h in raw:
            row = rows.get(h.chunk_id)
            if row is None:  # vector without canonical row: ignore rather than cite unverifiable text
                continue
            m = h.metadata
            sd = date.fromisoformat(m["source_date"]) if m.get("source_date") else None
            out.append(Hit(row.id, row.document_id, m.get("title", ""), m.get("department", ""), sd, row.page_number,
                           row.chunk_index, h.similarity, h.distance, row.content))
        return out

    @staticmethod
    def _dedupe(hits: list[Hit]) -> list[Hit]:
        kept: list[Hit] = []
        for h in sorted(hits, key=lambda x: x.score, reverse=True):
            if any(k.document_id == h.document_id and k.page_number == h.page_number and abs(k.chunk_index - h.chunk_index) <= 1 for k in kept):
                continue
            kept.append(h)
        return kept

    def search(self, query: str, department: str | None = None, top_k: int = 5) -> RetrievalResult:
        q = normalize_query(query)
        if not q:
            return RetrievalResult(metrics=RetrievalMetrics(metric=self.vectors.metric, threshold=self.threshold, decision="no_query"))
        where = {"department": department} if department else None
        vec = self.embedder.embed_query(q)
        hits = self._dedupe(self._to_hits(self.vectors.query(vec, top_k * 3, where)))

        # Supersession: a newer valid circular replaces the older one it revises.
        final: list[Hit] = []
        for h in hits:
            newer = self._newest_replacement(h.document_id)
            if newer is None:
                final.append(h)
                continue
            extra = self._to_hits(self.vectors.query(vec, 2, {"document_id": newer.id}))
            note = f"'{newer.title}' ({newer.source_date.isoformat()}) replaces '{h.title}' ({h.source_date.isoformat() if h.source_date else 'undated'})."
            for e in extra:
                e.superseded_note = note
                final.append(e)
        for h in final:  # a newer document that replaced an older one gets an explanatory note
            if h.superseded_note is None:
                d = self.db.get(Document, h.document_id)
                old = self.db.get(Document, d.supersedes_id) if d is not None and d.supersedes_id else None
                if old is not None:
                    h.superseded_note = f"This document replaces '{old.title}' ({old.source_date.isoformat()})."
        final = self._dedupe(final)[:top_k]
        top = final[0].score if final else None
        return RetrievalResult(
            hits=final,
            metrics=RetrievalMetrics(metric=self.vectors.metric, top_score=round(top, 4) if top is not None else None,
                                     hits=len(final), threshold=self.threshold),
        )

    def adequate(self, result: RetrievalResult) -> list[Hit]:
        return [h for h in result.hits if h.score >= self.threshold]
