"""Lightweight language resolution for text chat.

Telugu is identified by its Unicode block (U+0C00 to U+0C7F). This is a Phase 1 heuristic
for typed text; in Phase 2 the speech service reports the language of voice input.
"""
from __future__ import annotations

from typing import Literal

Lang = Literal["en", "te"]
TELUGU_RANGE = (0x0C00, 0x0C7F)
# Mixed Telugu-English input is treated as Telugu once Telugu is a meaningful share of letters.
TELUGU_SHARE_THRESHOLD = 0.3


def detect_language(text: str) -> Lang:
    telugu = latin = 0
    for ch in text:
        cp = ord(ch)
        if TELUGU_RANGE[0] <= cp <= TELUGU_RANGE[1]:
            telugu += 1
        elif ch.isalpha() and cp < 0x250:
            latin += 1
    letters = telugu + latin
    if letters == 0:
        return "en"
    return "te" if telugu / letters >= TELUGU_SHARE_THRESHOLD else "en"


def resolve_language(text: str, requested: str = "auto") -> Lang:
    if requested in ("en", "te"):
        return requested  # type: ignore[return-value]
    return detect_language(text)
