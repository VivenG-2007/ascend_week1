"""Measure retrieval scores on a labelled validation set and suggest SIMILARITY_THRESHOLD.

    python -m app.scripts.tune_threshold            # uses data/validation_questions.json

Scores are cosine SIMILARITY (1 - distance in Chroma's cosine space). Run this with the REAL embedding model
(EMBEDDING_PROVIDER=e5) after seeding documents; results with the offline `hash` embedder are not representative."""
from __future__ import annotations

import json
from pathlib import Path

from app.db.session import get_sessionmaker
from app.services.embeddings import get_embedder
from app.services.retrieval import RetrievalService
from app.services.vectorstore import get_vectorstore

PATH = Path(__file__).resolve().parents[3] / "data" / "validation_questions.json"


def main() -> None:
    items = json.loads(PATH.read_text(encoding="utf-8"))
    emb, vs = get_embedder(), get_vectorstore()
    rows = []
    with get_sessionmaker()() as db:
        svc = RetrievalService(db, emb, vs, 0.0)
        for it in items:
            res = svc.search(it["question"])
            rows.append((it["question"], it["answerable"], res.metrics.top_score or 0.0))
    pos = sorted(s for _, a, s in rows if a)
    neg = sorted(s for _, a, s in rows if not a)
    print(f"embedder={emb.name} metric=cosine_similarity  answerable={len(pos)} unanswerable={len(neg)}")
    for q, a, s in sorted(rows, key=lambda r: r[2]):
        print(f"  {s:.3f}  {'ANSWERABLE  ' if a else 'unanswerable'}  {q}")
    best = None
    for k in range(0, 101):
        th = k / 100
        tp = sum(1 for s in pos if s >= th); fp = sum(1 for s in neg if s >= th)
        # prefer never answering from irrelevant evidence, then maximise answerable coverage
        score = (-fp, tp)
        if best is None or score > best[0]:
            best = (score, th, tp, fp)
    _, th, tp, fp = best
    print(f"\nSuggested SIMILARITY_THRESHOLD ~= {th:.2f}  (answerable kept {tp}/{len(pos)}, unanswerable leaking {fp}/{len(neg)})")
    if pos and neg and min(pos) <= max(neg):
        print("WARNING: score ranges overlap; no threshold separates this set cleanly. Add documents/chunks or review the model.")


if __name__ == "__main__":
    main()
