"""Caption tokenisation and word-shingle helpers for duplicate detection."""

from __future__ import annotations

import re
import unicodedata


# Keep hashtags and words as tokens, and retain common emoji/symbol code points.
# Punctuation is omitted, so "great-day" and "great day" compare alike.
TOKEN_PATTERN = re.compile(
    r"#[\w]+|[\w]+|[\U0001F000-\U0001FAFF\u2600-\u27BF]", re.UNICODE
)


def normalize_caption(caption: str) -> str:
    """Normalize case, Unicode and spacing while retaining hashtags and emoji.

    NFKC combines compatible Unicode forms; punctuation not part of a hashtag
    is treated as whitespace. Emoji and symbols are retained as tokens.
    """
    normalized = unicodedata.normalize("NFKC", caption).casefold()
    tokens = TOKEN_PATTERN.findall(normalized)
    return " ".join(tokens)


def tokenize_caption(caption: str) -> list[str]:
    """Return normalized word, hashtag and symbol tokens."""
    normalized = normalize_caption(caption)
    return normalized.split() if normalized else []


def create_shingles(tokens: list[str], shingle_size: int = 3) -> set[tuple[str, ...]]:
    """Create unique n-gram shingles; short captions use their full token span."""
    if shingle_size < 1:
        raise ValueError("shingle_size must be at least 1")
    if not tokens:
        return set()
    width = min(shingle_size, len(tokens))
    return {tuple(tokens[index:index + width]) for index in range(len(tokens) - width + 1)}
