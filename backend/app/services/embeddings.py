"""Embedding providers. Models are loaded once and reused (never per request).

Providers:
  azure  — Azure OpenAI / Azure AI Foundry text-embedding model (requires credentials)
  hash   — Deterministic lexical embedder for offline development and automated tests ONLY
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from functools import lru_cache
from typing import Protocol

from app.config import get_settings

log = logging.getLogger("campusvoice.embeddings")


class Embedder(Protocol):
    name: str
    dimension: int

    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class HashEmbedder:
    """Deterministic lexical embedder (hashed word and character n-grams).

    For offline development and automated tests ONLY. It has no cross-language understanding,
    so English questions will not match Telugu documents. Use EMBEDDING_PROVIDER=azure for real behaviour.
    """

    name = "hash-384"
    dimension = 384
    _tok = re.compile(r"\w+", re.UNICODE)

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dimension
        words = self._tok.findall(text.lower())
        feats = list(words)
        for w in words:
            padded = f"#{w}#"
            feats += [padded[i : i + 3] for i in range(max(1, len(padded) - 2))]
        for f in feats:
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "big")
            v[h % self.dimension] += 1.0 if (h >> 40) & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


class AzureEmbedder:
    """Azure OpenAI / Azure AI Foundry text-embedding model (e.g. text-embedding-3-large).

    Requires the same endpoint + API key as the LLM deployment
    (AZURE_AI_FOUNDRY_ENDPOINT + AZURE_AI_FOUNDRY_API_KEY).
    Set AZURE_EMBEDDING_DEPLOYMENT to your deployment name.
    """

    _BATCH = 16  # Azure accepts up to 2048 texts per call; 16 is conservative for large docs

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str,
        dimension: int,
    ) -> None:
        log.info(
            "Initialising AzureEmbedder deployment=%s endpoint=%s dimension=%d",
            deployment,
            endpoint,
            dimension,
        )
        try:
            from openai import AzureOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai is not installed. Run: pip install openai"
            ) from exc
        self.name = f"azure/{deployment}"
        self.dimension = dimension
        self._deployment = deployment
        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        log.info("AzureEmbedder ready: %s", self.name)

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        log.debug("AzureEmbedder: embedding batch of %d texts via deployment=%s", len(texts), self._deployment)
        resp = self._client.embeddings.create(
            model=self._deployment,
            input=texts,
            dimensions=self.dimension,
        )
        vecs = [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
        log.debug("AzureEmbedder: batch complete — %d vectors returned (dim=%d)", len(vecs), self.dimension)
        return vecs

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        log.debug("AzureEmbedder.embed_passages: %d texts total", len(texts))
        result: list[list[float]] = []
        for i in range(0, len(texts), self._BATCH):
            result.extend(self._embed_batch(texts[i : i + self._BATCH]))
        return result

    def embed_query(self, text: str) -> list[float]:
        log.debug("AzureEmbedder.embed_query: %d chars", len(text))
        return self._embed_batch([text])[0]


@lru_cache
def get_embedder() -> Embedder:
    s = get_settings()
    if s.embedding_provider == "hash":
        log.info("Using HashEmbedder (offline/test mode — no cross-language search)")
        return HashEmbedder()
    if s.embedding_provider == "azure":
        if not s.azure_embedding_configured:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=azure but AZURE_AI_FOUNDRY_ENDPOINT, AZURE_AI_FOUNDRY_API_KEY "
                "or AZURE_EMBEDDING_DEPLOYMENT is missing. Set these env vars or use EMBEDDING_PROVIDER=hash."
            )
        return AzureEmbedder(
            endpoint=s.azure_ai_foundry_endpoint,        # type: ignore[arg-type]
            api_key=s.azure_ai_foundry_api_key,          # type: ignore[arg-type]
            deployment=s.azure_embedding_deployment,     # type: ignore[arg-type]
            api_version=s.azure_ai_foundry_api_version,
            dimension=s.azure_embedding_dimension,
        )
    raise RuntimeError(
        f"Unknown EMBEDDING_PROVIDER={s.embedding_provider!r}. "
        "Use 'azure' (production) or 'hash' (offline/tests)."
    )
