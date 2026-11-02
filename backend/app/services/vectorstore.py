"""ChromaDB wrapper — Chroma Cloud (CloudClient), self-hosted (HttpClient), or local (PersistentClient).

Collections use cosine space, where distance = 1 - cosine similarity, so we report
similarity = 1 - distance (higher is better).

Priority:
  1. Chroma Cloud (api.trychroma.com) — set CHROMA_API_KEY + CHROMA_TENANT + CHROMA_DATABASE.
  2. Self-hosted HttpClient             — set CHROMA_HOST (+ optional CHROMA_PORT / CHROMA_SSL).
  3. Local PersistentClient             — fallback, uses CHROMA_PERSIST_DIRECTORY.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

from app.config import BACKEND_DIR, get_settings

log = logging.getLogger("campusvoice.vectorstore")


@dataclass
class VectorHit:
    chunk_id: str
    distance: float
    similarity: float
    metadata: dict[str, Any]


class VectorStore:
    def __init__(
        self,
        *,
        path: str | None = None,
        host: str | None = None,
        port: int = 8001,
        ssl: bool = False,
        api_key: str | None = None,
        tenant: str | None = None,
        database: str | None = None,
        collection: str,
    ) -> None:
        if api_key and tenant and database:
            # Chroma Cloud via CloudClient (api.trychroma.com)
            log.info(
                "Connecting to Chroma Cloud (CloudClient) tenant=%s database=%s",
                tenant,
                database,
            )
            self._client = chromadb.CloudClient(
                api_key=api_key,
                tenant=tenant,
                database=database,
            )
            log.info("Chroma Cloud CloudClient connected tenant=%s database=%s", tenant, database)
        elif host:
            log.info("Connecting to ChromaDB self-hosted host=%s port=%d ssl=%s", host, port, ssl)
            self._client = chromadb.HttpClient(host=host, port=port, ssl=ssl)
            log.info("ChromaDB HttpClient connected to %s:%d", host, port)
        else:
            p = Path(path or "./chroma_data")
            if not p.is_absolute():
                p = BACKEND_DIR / p
            p.mkdir(parents=True, exist_ok=True)
            log.info("Using local ChromaDB PersistentClient at %s", p)
            self._client = chromadb.PersistentClient(path=str(p))

        self._col = self._client.get_or_create_collection(
            collection, configuration={"hnsw": {"space": "cosine"}}
        )
        self.metric = "cosine_similarity"
        log.info("ChromaDB collection=%r vectors=%d", collection, self._col.count())

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        log.debug("VectorStore.upsert: %d vectors (dim=%d)", len(ids), len(embeddings[0]) if embeddings else 0)
        self._col.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        log.debug("VectorStore.upsert: done, collection now has %d vectors", self._col.count())

    def query(self, embedding: list[float], n_results: int, where: dict | None = None) -> list[VectorHit]:
        total = self._col.count()
        if total == 0:
            log.debug("VectorStore.query: collection is empty — skipping")
            return []
        actual = min(n_results, total)
        log.debug("VectorStore.query: n_results=%d (capped=%d, total=%d)", n_results, actual, total)
        res = self._col.query(
            query_embeddings=[embedding],
            n_results=actual,
            where=where,
            include=["distances", "metadatas"],
        )
        hits = [
            VectorHit(cid, float(d), 1.0 - float(d), dict(m or {}))
            for cid, d, m in zip(res["ids"][0], res["distances"][0], res["metadatas"][0])
        ]
        if hits:
            log.debug(
                "VectorStore.query: %d hits, top similarity=%.4f",
                len(hits),
                hits[0].similarity,
            )
        return hits

    def delete_document(self, document_id: str) -> None:
        log.debug("VectorStore.delete_document: document_id=%s", document_id)
        self._col.delete(where={"document_id": document_id})

    def update_document_metadata(self, document_id: str, metadata: dict[str, Any]) -> None:
        got = self._col.get(where={"document_id": document_id}, include=["metadatas"])
        if got["ids"]:
            log.debug("VectorStore.update_document_metadata: updating %d chunks for document=%s", len(got["ids"]), document_id)
            self._col.update(ids=got["ids"], metadatas=[{**m, **metadata} for m in got["metadatas"]])

    def count(self) -> int:
        return self._col.count()

    def count_document(self, document_id: str) -> int:
        return len(self._col.get(where={"document_id": document_id}, include=[])["ids"])


@lru_cache
def get_vectorstore() -> VectorStore:
    s = get_settings()
    if s.chroma_cloud_configured:
        log.info("VectorStore: using Chroma Cloud (api.trychroma.com)")
        return VectorStore(
            api_key=s.chroma_api_key,
            tenant=s.chroma_tenant,
            database=s.chroma_database,
            collection=s.chroma_collection_name,
        )
    log.info(
        "VectorStore: %s",
        f"self-hosted HttpClient host={s.chroma_host}" if s.chroma_host else f"local PersistentClient path={s.chroma_persist_directory}",
    )
    return VectorStore(
        path=s.chroma_persist_directory if not s.chroma_host else None,
        host=s.chroma_host or None,
        port=s.chroma_port,
        ssl=s.chroma_ssl,
        collection=s.chroma_collection_name,
    )

