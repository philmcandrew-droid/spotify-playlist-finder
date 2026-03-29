"""
Social media search: Facebook, Instagram, TikTok, Twitter/X via DuckDuckGo.
No API keys required.
"""
import re
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed


PLATFORMS = {
    "facebook": {
        "label": "Facebook",
        "sites": ["facebook.com"],
    },
    "instagram": {
        "label": "Instagram",
        "sites": ["instagram.com"],
    },
    "tiktok": {
        "label": "TikTok",
        "sites": ["tiktok.com"],
    },
    "twitter": {
        "label": "Twitter / X",
        "sites": ["twitter.com", "x.com"],
    },
}


def _parse_quoted(s: str) -> tuple[str, bool]:
    s = (s or "").strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1].strip(), True
    return s, False


def run_social_search(query: str, max_results: int = 25) -> dict[str, Any]:
    raw_q = (query or "").strip()
    if not raw_q:
        return {"error": "Search query is required"}
    q, is_exact = _parse_quoted(raw_q)
    if not q:
        return {"error": "Search query is required"}
    n = max(1, min(int(max_results), 100))

    results: dict[str, list[dict]] = {}
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_search_platform, platform, q, n, is_exact): platform
            for platform in PLATFORMS
        }
        for fut in as_completed(futures):
            platform = futures[fut]
            try:
                results[platform] = fut.result()
            except Exception as e:
                errors.append(f"{platform}: {e}")
                results[platform] = []

    if is_exact:
        exact_lower = q.lower()
        for platform in results:
            results[platform] = _filter_exact(results[platform], exact_lower)

    total = sum(len(v) for v in results.values())
    return {
        "mode": "social",
        "query": raw_q,
        "exact_match": is_exact,
        "total": total,
        "facebook": results.get("facebook", []),
        "instagram": results.get("instagram", []),
        "tiktok": results.get("tiktok", []),
        "twitter": results.get("twitter", []),
        "errors": errors if errors else None,
    }


def _filter_exact(items: list[dict], exact_lower: str) -> list[dict]:
    return [
        item for item in items
        if exact_lower in (item.get("title") or "").lower()
        or exact_lower in (item.get("snippet") or "").lower()
    ]


def _search_platform(platform: str, query: str, max_results: int, exact: bool) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        return []

    cfg = PLATFORMS[platform]
    site_filter = " OR ".join(f"site:{s}" for s in cfg["sites"])
    phrase = f'"{query}"' if exact else query
    search_q = f'{phrase} ({site_filter})'

    try:
        raw = DDGS().text(search_q, max_results=max_results)
    except Exception:
        try:
            raw = DDGS().text(f"{query} ({site_filter})", max_results=max_results)
        except Exception:
            return []

    seen: set[str] = set()
    out: list[dict] = []
    for r in (raw or []):
        url = (r.get("href") or "").split("?")[0].split("#")[0].rstrip("/").lower()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append({
            "title": r.get("title") or "",
            "url": r.get("href") or "",
            "snippet": (r.get("body") or "")[:600],
            "platform": platform,
        })
    return out
