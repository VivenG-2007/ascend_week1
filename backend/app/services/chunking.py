"""Page-aware chunking (about 500 tokens with overlap). Chunks never cross page boundaries,
so every chunk keeps an exact page number for citations."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

TELUGU = re.compile(r"[\u0c00-\u0c7f]")
_SENTENCE = re.compile(r"(?<=[.!?।])\s+")


def estimate_tokens(text: str) -> int:
    """Rough model-agnostic estimate: ~4 Latin chars/token, ~1.5 Telugu chars/token."""
    telugu = len(TELUGU.findall(text))
    return math.ceil((len(text) - telugu) / 4 + telugu / 1.5)


@dataclass(frozen=True)
class ChunkDraft:
    page_number: int
    chunk_index: int
    content: str
    token_count: int


def _units(text: str, max_tokens: int) -> list[str]:
    units: list[str] = []
    for para in re.split(r"\n+", text):
        para = para.strip()
        if not para:
            continue
        for sent in _SENTENCE.split(para):
            sent = sent.strip()
            if not sent:
                continue
            if estimate_tokens(sent) <= max_tokens:
                units.append(sent)
            else:  # oversize sentence: split on words
                words, cur = sent.split(), []
                for w in words:
                    cur.append(w)
                    if estimate_tokens(" ".join(cur)) >= max_tokens:
                        units.append(" ".join(cur))
                        cur = []
                if cur:
                    units.append(" ".join(cur))
    return units


def chunk_pages(pages: list[tuple[int, str]], max_tokens: int = 500, overlap_tokens: int = 60) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    idx = 0
    for page_number, text in pages:
        units = _units(text, max_tokens)
        cur: list[str] = []
        cur_tokens = 0
        for unit in units:
            t = estimate_tokens(unit)
            if cur and cur_tokens + t > max_tokens:
                content = "\n".join(cur)
                drafts.append(ChunkDraft(page_number, idx, content, estimate_tokens(content)))
                idx += 1
                # carry trailing units as overlap
                carry, carried = [], 0
                for u in reversed(cur):
                    ut = estimate_tokens(u)
                    if carried + ut > overlap_tokens:
                        break
                    carry.insert(0, u)
                    carried += ut
                cur, cur_tokens = carry, carried
            cur.append(unit)
            cur_tokens += t
        if cur and any(u.strip() for u in cur):
            content = "\n".join(cur)
            drafts.append(ChunkDraft(page_number, idx, content, estimate_tokens(content)))
            idx += 1
    return drafts
