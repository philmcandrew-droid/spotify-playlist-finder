"""
Deep search: find mentions on archived forums, old websites, and the Internet Archive.
Uses DuckDuckGo (no API key) and the Internet Archive search API.
"""
import os
import re
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

FORUM_SITES = [
    "reddit.com",
    "last.fm",
    "rateyourmusic.com",
    "discogs.com",
    "genius.com",
    "songmeanings.com",
    "ultimate-guitar.com",
    "musicbrainz.org",
    "albumoftheyear.org",
    "sputnikmusic.com",
    "hydrogenaud.io",
    "forums.stevehoffman.tv",
    "kvraudio.com",
    "gearslutz.com",
    "tapeop.com",
    "soundonsound.com",
]

WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"


def _parse_quoted(s: str) -> tuple[str, bool]:
    """If wrapped in double quotes, return (inner, True) for exact match."""
    s = (s or "").strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1].strip(), True
    return s, False


def run_deep_search(query: str, max_results: int = 25) -> dict[str, Any]:
    raw_q = (query or "").strip()
    if not raw_q:
        return {"error": "Search query is required"}
    q, is_exact = _parse_quoted(raw_q)
    if not q:
        return {"error": "Search query is required"}
    n = max(1, min(int(max_results), 100))

    forum_results: list[dict] = []
    general_results: list[dict] = []
    archive_results: list[dict] = []
    wayback_results: list[dict] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_search_ddg_forums, q, n, is_exact): "forums",
            pool.submit(_search_ddg_general, q, n, is_exact): "general",
            pool.submit(_search_archive_org, q, min(n, 30), is_exact): "archive",
            pool.submit(_search_wayback, q, min(n, 20)): "wayback",
        }
        for fut in as_completed(futures):
            label = futures[fut]
            try:
                results = fut.result()
            except Exception as e:
                errors.append(f"{label}: {e}")
                continue
            if label == "forums":
                forum_results = results
            elif label == "general":
                general_results = results
            elif label == "archive":
                archive_results = results
            elif label == "wayback":
                wayback_results = results

    seen_urls: set[str] = set()
    forum_results = _dedup(forum_results, seen_urls)
    general_results = _dedup(general_results, seen_urls)

    if is_exact:
        exact_lower = q.lower()
        forum_results = _filter_exact(forum_results, exact_lower)
        general_results = _filter_exact(general_results, exact_lower)
        archive_results = _filter_exact_archive(archive_results, exact_lower)

    return {
        "mode": "deep_search",
        "query": raw_q,
        "exact_match": is_exact,
        "forum_results": forum_results,
        "general_results": general_results,
        "archive_results": archive_results,
        "wayback_results": wayback_results,
        "errors": errors if errors else None,
    }


def _dedup(items: list[dict], seen: set[str]) -> list[dict]:
    out = []
    for item in items:
        url = (item.get("url") or "").split("?")[0].split("#")[0].rstrip("/").lower()
        if url and url not in seen:
            seen.add(url)
            out.append(item)
    return out


def _filter_exact(items: list[dict], exact_lower: str) -> list[dict]:
    """Keep only results whose title or snippet contain the exact phrase."""
    return [
        item for item in items
        if exact_lower in (item.get("title") or "").lower()
        or exact_lower in (item.get("snippet") or "").lower()
    ]


def _filter_exact_archive(items: list[dict], exact_lower: str) -> list[dict]:
    return [
        item for item in items
        if exact_lower in (item.get("title") or "").lower()
        or exact_lower in (item.get("description") or "").lower()
    ]


def _search_ddg_forums(query: str, max_results: int, exact: bool) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        return []
    site_filter = " OR ".join(f"site:{s}" for s in FORUM_SITES[:8])
    phrase = f'"{query}"' if exact else query
    search_q = f'{phrase} ({site_filter})'
    try:
        raw = DDGS().text(search_q, max_results=max_results)
    except Exception:
        raw = DDGS().text(f"{query} ({site_filter})", max_results=max_results)
    return [_ddg_to_result(r, "forum") for r in (raw or [])]


def _search_ddg_general(query: str, max_results: int, exact: bool) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        return []
    phrase = f'"{query}"' if exact else query
    search_q = f'{phrase} forum OR discussion OR review OR thread OR archive'
    try:
        raw = DDGS().text(search_q, max_results=max_results)
    except Exception:
        raw = DDGS().text(f"{query} forum discussion review", max_results=max_results)
    return [_ddg_to_result(r, "web") for r in (raw or [])]


def _ddg_to_result(row: dict, source: str) -> dict:
    return {
        "title": row.get("title") or "",
        "url": row.get("href") or "",
        "snippet": (row.get("body") or "")[:600],
        "source": source,
    }


def _search_archive_org(query: str, max_results: int, exact: bool = False) -> list[dict]:
    q_str = f'"{query}"' if exact else query
    params = {
        "q": q_str,
        "fl[]": ["identifier", "title", "description", "date", "mediatype", "collection"],
        "rows": max_results,
        "output": "json",
        "sort[]": "downloads desc",
    }
    try:
        r = requests.get(ARCHIVE_SEARCH, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    docs = (data.get("response") or {}).get("docs") or []
    out = []
    for doc in docs:
        ident = doc.get("identifier") or ""
        if not ident:
            continue
        desc = doc.get("description") or ""
        if isinstance(desc, list):
            desc = " ".join(desc)
        desc = re.sub(r"<[^>]+>", "", desc)[:600]
        out.append({
            "title": doc.get("title") or ident,
            "url": f"https://archive.org/details/{ident}",
            "description": desc,
            "date": (doc.get("date") or "")[:10],
            "mediatype": doc.get("mediatype") or "",
            "source": "archive_org",
        })
    return out


def _search_wayback(query: str, max_results: int) -> list[dict]:
    """Search the Wayback Machine CDX API for archived pages mentioning the query."""
    params = {
        "url": f"*.com",
        "matchType": "domain",
        "output": "json",
        "limit": max_results,
        "filter": f"original:.*{_url_safe(query)}.*",
        "fl": "original,timestamp,statuscode,mimetype",
        "collapse": "urlkey",
    }
    try:
        r = requests.get(WAYBACK_CDX, params=params, timeout=20)
        r.raise_for_status()
        rows = r.json()
    except Exception:
        return _search_wayback_simple(query, max_results)
    if not rows or len(rows) < 2:
        return _search_wayback_simple(query, max_results)
    header = rows[0]
    out = []
    for row in rows[1:]:
        entry = dict(zip(header, row))
        original = entry.get("original") or ""
        ts = entry.get("timestamp") or ""
        if not original or not ts:
            continue
        wb_url = f"https://web.archive.org/web/{ts}/{original}"
        date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ""
        out.append({
            "title": original,
            "url": wb_url,
            "original_url": original,
            "date": date,
            "source": "wayback",
        })
    return out


def _search_wayback_simple(query: str, max_results: int) -> list[dict]:
    """Fallback: search Wayback for specific known forum domains."""
    domains = ["reddit.com", "last.fm", "rateyourmusic.com", "discogs.com",
               "forums.stevehoffman.tv", "sputnikmusic.com"]
    out = []
    safe_q = _url_safe(query)
    for domain in domains[:4]:
        if len(out) >= max_results:
            break
        params = {
            "url": f"{domain}/*{safe_q}*",
            "matchType": "url",
            "output": "json",
            "limit": min(5, max_results - len(out)),
            "fl": "original,timestamp",
            "collapse": "urlkey",
            "filter": "statuscode:200",
        }
        try:
            r = requests.get(WAYBACK_CDX, params=params, timeout=10)
            if r.status_code != 200:
                continue
            rows = r.json()
        except Exception:
            continue
        if not rows or len(rows) < 2:
            continue
        header = rows[0]
        for row in rows[1:]:
            entry = dict(zip(header, row))
            original = entry.get("original") or ""
            ts = entry.get("timestamp") or ""
            if not original:
                continue
            wb_url = f"https://web.archive.org/web/{ts}/{original}"
            date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ""
            out.append({
                "title": original,
                "url": wb_url,
                "original_url": original,
                "date": date,
                "source": "wayback",
            })
    return out


def _url_safe(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "+", s.strip().lower())
