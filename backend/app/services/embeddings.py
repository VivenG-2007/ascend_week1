"""
Multilingual Text Embedding Service
Uses intfloat/multilingual-e5-small for English and Telugu semantic retrieval.
Includes a word-hash random projection fallback for fast automated testing and offline demo resilience.
"""
import os
import sys
import re
import hashlib
import logging
from typing import List
import numpy as np

logger = logging.getLogger("campusvoice.embeddings")

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        if "pytest" in sys.modules or os.getenv("TESTING") == "1":
            _model = "fallback"
            return _model
        try:
            from sentence_transformers import SentenceTransformer
            from app.config import settings
            logger.info(f"[EMBEDDINGS] Loading {settings.EMBEDDING_MODEL_NAME}...")
            _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            logger.info(f"[EMBEDDINGS] Successfully loaded {settings.EMBEDDING_MODEL_NAME}.")
        except Exception as e:
            logger.warning(f"[EMBEDDINGS] Failed to load local sentence-transformers model: {e}. Falling back to lexical projection for demo resilience.")
            _model = "fallback"
    return _model

STOP_WORDS = {
    "when", "what", "where", "which", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if",
    "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after", "above", "below",
    "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "all", "any", "both", "each", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"
}

def _text_to_feature_vector(text: str, dim: int = 384) -> List[float]:
    """Generates a 384-dimensional normalized salient feature projection."""
    cleaned = re.sub(r'^(passage:|query:)\s*', '', text.strip(), flags=re.IGNORECASE)
    all_words = re.findall(r'\w+', cleaned.lower())
    words = [w for w in all_words if w not in STOP_WORDS and len(w) >= 3]
    if not words:
        words = all_words

    vec = np.ones(dim, dtype=np.float32) * 0.05
    if not words:
        vec[0] = 1.0
        norm = np.linalg.norm(vec)
        return (vec / norm).tolist()
    for w in words:
        h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16) % dim
        vec[h] += 1.5
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

def generate_passage_embeddings(texts: List[str]) -> List[List[float]]:
    """Generates normalized vector embeddings for document chunks (prefixed with 'passage: ')."""
    model = get_embedding_model()
    if model != "fallback":
        prefixed = [f"passage: {t.strip()}" for t in texts]
        embeddings = model.encode(prefixed, normalize_embeddings=True)
        return embeddings.tolist()
    else:
        return [_text_to_feature_vector(t) for t in texts]

def generate_query_embedding(query: str) -> List[float]:
    """Generates normalized vector embedding for user question (prefixed with 'query: ')."""
    model = get_embedding_model()
    if model != "fallback":
        prefixed = f"query: {query.strip()}"
        embedding = model.encode(prefixed, normalize_embeddings=True)
        return embedding.tolist()
    else:
        return _text_to_feature_vector(query)
