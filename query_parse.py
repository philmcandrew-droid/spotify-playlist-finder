"""Shared query cleanup for every search source."""
from __future__ import annotations

import re

_OPEN_QUOTES = '"“„«'
_CLOSE_QUOTES = '"”»'
_MAX_LEN = 200


def normalize_query(s: str) -> str:
    text = (s or "").replace("\u00a0", " ")
    text = " ".join(text.split())
    return text[:_MAX_LEN]


def parse_quoted(s: str) -> tuple[str, bool]:
    """Return (phrase, exact). Exact is true when the whole query is wrapped in quotes."""
    text = normalize_query(s)
    if len(text) >= 2 and text[0] in _OPEN_QUOTES and text[-1] in _CLOSE_QUOTES:
        inner = normalize_query(text[1:-1])
        if inner:
            return inner, True
    return text, False


def phrase_in_text(*parts: str, phrase: str) -> bool:
    needle = (phrase or "").strip().lower()
    if not needle:
        return False
    haystack = " ".join(part or "" for part in parts).lower()
    return needle in haystack


def playlist_name_score(name: str, phrase: str) -> int:
    """Higher is a closer title match. 0 means the title does not include the phrase tokens."""
    title = (name or "").strip().lower()
    query = (phrase or "").strip().lower()
    if not title or not query:
        return 0
    if title == query:
        return 400
    if title.startswith(query + " ") or title.startswith(query + "—") or title.startswith(query + "-"):
        return 300
    if query in title:
        return 200
    tokens = [t for t in re.split(r"\s+", query) if t]
    if tokens and all(t in title for t in tokens):
        return 100
    return 0


def playlist_search_queries(phrases: list[str], exact: bool) -> list[str]:
    """Quoted form first when the user asked for an exact name."""
    out: list[str] = []
    for raw in phrases:
        phrase = normalize_query(raw)
        if not phrase:
            continue
        variants = [f'"{phrase}"', phrase] if exact else [phrase]
        for item in variants:
            if item not in out:
                out.append(item)
    return out
