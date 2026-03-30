"""
Global Search – aggregates results from top search engines and web crawlers.

Search engines:
  Google   – via Custom Search JSON API (optional: GOOGLE_API_KEY + GOOGLE_CSE_ID)
  Yahoo    – scraped HTML
  DuckDuckGo – via ddgs library (Bing-powered)
  DuckDuckGo News – latest/trending results
  Mojeek   – independent crawler, scraped HTML

Web crawlers:
  Common Crawl, Wayback Machine CDX, Marginalia.
"""

import json
import os
import re
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote as url_quote

import requests

_TIMEOUT = 15
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/124.0.0.0 Safari/537.36")

WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"


def _parse_quoted(s: str) -> tuple[str, bool]:
    s = (s or "").strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1].strip(), True
    return s, False


def _filter_exact(items: list[dict], phrase_lower: str) -> list[dict]:
    return [
        r for r in items
        if phrase_lower in (r.get("title") or "").lower()
        or phrase_lower in (r.get("snippet") or "").lower()
        or phrase_lower in (r.get("url") or "").lower()
    ]


def _dedup(items: list[dict], seen: set[str]) -> list[dict]:
    out = []
    for item in items:
        url = (item.get("url") or "").split("?")[0].split("#")[0].rstrip("/").lower()
        if url and url not in seen:
            seen.add(url)
            out.append(item)
    return out


# ── Search Engines ──────────────────────────────────────────────────────────


def _search_google_api(query: str, max_results: int, exact: bool) -> list[dict]:
    """Google Custom Search JSON API (free 100 queries/day).
    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID env vars."""
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        return []
    phrase = f'"{query}"' if exact else query
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": api_key, "cx": cse_id, "q": phrase,
                    "num": min(max_results, 10)},
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [
            {"title": r.get("title", ""), "url": r.get("link", ""),
             "snippet": r.get("snippet", ""), "source": "Google"}
            for r in data.get("items", [])[:max_results]
        ]
    except Exception:
        return []


def _search_yahoo(query: str, max_results: int, exact: bool) -> list[dict]:
    """Yahoo search via HTML scraping."""
    try:
        from bs4 import BeautifulSoup
        phrase = f'"{query}"' if exact else query
        resp = requests.get(
            "https://search.yahoo.com/search",
            params={"p": phrase, "n": min(max_results, 30)},
            headers={"User-Agent": _UA,
                     "Accept": "text/html,application/xhtml+xml",
                     "Accept-Language": "en-US,en;q=0.9"},
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for div in soup.select("div.algo, div.dd.algo, li div.compTitle"):
            title_el = div.select_one("h3 a") or div.select_one("a")
            snippet_el = (div.select_one("div.compText p")
                          or div.select_one("p")
                          or div.select_one("span.fc-falcon"))
            if not title_el:
                continue
            href = title_el.get("href", "")
            if not href:
                continue
            results.append({
                "title": title_el.get_text(strip=True),
                "url": href,
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                "source": "Yahoo",
            })
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def _search_ddg_web(query: str, max_results: int, exact: bool) -> list[dict]:
    try:
        from ddgs import DDGS
        phrase = f'"{query}"' if exact else query
        raw = DDGS().text(phrase, max_results=max_results)
        return [
            {"title": r.get("title", ""), "url": r.get("href", ""),
             "snippet": (r.get("body") or "")[:500], "source": "DuckDuckGo"}
            for r in (raw or [])
        ]
    except Exception:
        return []


def _search_ddg_news(query: str, max_results: int, exact: bool) -> list[dict]:
    try:
        from ddgs import DDGS
        phrase = f'"{query}"' if exact else query
        raw = DDGS().news(phrase, max_results=max_results)
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""),
             "snippet": (r.get("body") or "")[:500],
             "date": r.get("date", ""), "source": "Latest News"}
            for r in (raw or [])
        ]
    except Exception:
        return []


def _search_mojeek(query: str, max_results: int, exact: bool) -> list[dict]:
    """Mojeek – independent search engine with its own web crawler."""
    try:
        from bs4 import BeautifulSoup
        phrase = f'"{query}"' if exact else query
        resp = requests.get(
            "https://www.mojeek.com/search",
            params={"q": phrase},
            headers={"User-Agent": _UA,
                     "Accept": "text/html,application/xhtml+xml",
                     "Accept-Language": "en-US,en;q=0.9"},
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for li in soup.select("ul.results-standard li"):
            title_el = li.select_one("a.title")
            snippet_el = li.select_one("p.s")
            if not title_el:
                continue
            href = title_el.get("href", "")
            if not href:
                continue
            results.append({
                "title": title_el.get_text(strip=True),
                "url": href,
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                "source": "Mojeek",
            })
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


# ── Web Crawlers ────────────────────────────────────────────────────────────


def _search_commoncrawl(query: str, max_results: int) -> list[dict]:
    try:
        resp = requests.get(
            "https://index.commoncrawl.org/collinfo.json",
            headers={"User-Agent": _UA}, timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        indexes = resp.json()
        if not indexes:
            return []
        cdx_api = indexes[0]["cdx-api"]

        safe_q = re.sub(r"[^a-zA-Z0-9]", "-", query.strip().lower())
        resp = requests.get(
            cdx_api,
            params={"url": f"*{safe_q}*", "output": "json",
                    "limit": max_results},
            headers={"User-Agent": _UA}, timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return []

        results = []
        for line in resp.text.strip().split("\n"):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                url = record.get("url", "")
                ts = record.get("timestamp", "")
                date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ""
                results.append({
                    "title": url,
                    "url": url,
                    "snippet": (f"Crawled {date} | Status {record.get('status', '?')}"
                                f" | {record.get('mime', '')} | "
                                f"{record.get('length', '?')} bytes"),
                    "date": date,
                    "source": "Common Crawl",
                })
            except Exception:
                continue
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def _search_wayback(query: str, max_results: int) -> list[dict]:
    safe_q = re.sub(r"[^a-zA-Z0-9]", "+", query.strip().lower())
    params = {
        "url": f"*{safe_q}*", "output": "json", "limit": max_results,
        "fl": "original,timestamp,statuscode,mimetype",
        "filter": "statuscode:200", "collapse": "urlkey",
    }
    try:
        resp = requests.get(WAYBACK_CDX, params=params,
                            headers={"User-Agent": _UA}, timeout=_TIMEOUT)
        if resp.status_code != 200:
            return []
        rows = resp.json()
        if not rows or len(rows) < 2:
            return []
        header = rows[0]
        results = []
        for row in rows[1:]:
            entry = dict(zip(header, row))
            original = entry.get("original", "")
            ts = entry.get("timestamp", "")
            if not original or not ts:
                continue
            date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ""
            results.append({
                "title": original,
                "url": f"https://web.archive.org/web/{ts}/{original}",
                "snippet": f"Archived {date} | {entry.get('mimetype', '')}",
                "original_url": original,
                "date": date,
                "source": "Wayback Machine",
            })
        return results
    except Exception:
        return []


def _search_marginalia(query: str, max_results: int) -> list[dict]:
    try:
        resp = requests.get(
            f"https://api.marginalia.nu/public/search/{url_quote(query)}",
            params={"count": min(max_results, 20), "index": 0},
            headers={"User-Agent": _UA, "Accept": "application/json"},
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [
            {"title": r.get("title", "") or r.get("url", ""),
             "url": r.get("url", ""),
             "snippet": (r.get("description") or "")[:500],
             "source": "Marginalia"}
            for r in data.get("results", [])[:max_results]
        ]
    except Exception:
        return []


# ── Main entry point ────────────────────────────────────────────────────────


def run_global_search(query: str, max_results: int = 50) -> dict[str, Any]:
    raw_q = (query or "").strip()
    if not raw_q:
        return {"error": "Search query is required"}

    q, is_exact = _parse_quoted(raw_q)
    if not q:
        return {"error": "Search query is required"}

    n = max(1, min(int(max_results), 100))
    per = max(5, n // 4)

    engines_out: dict[str, list[dict]] = {}
    crawlers_out: dict[str, list[dict]] = {}
    errors: list[str] = []

    tasks: dict[str, tuple[str, Any, tuple]] = {
        "Google":          ("engine",  _search_google_api,  (q, per, is_exact)),
        "Yahoo":           ("engine",  _search_yahoo,       (q, per, is_exact)),
        "DuckDuckGo":      ("engine",  _search_ddg_web,     (q, per, is_exact)),
        "Latest News":     ("engine",  _search_ddg_news,    (q, per, is_exact)),
        "Mojeek":          ("engine",  _search_mojeek,      (q, per, is_exact)),
        "Common Crawl":    ("crawler", _search_commoncrawl, (q, per)),
        "Wayback Machine": ("crawler", _search_wayback,     (q, per)),
        "Marginalia":      ("crawler", _search_marginalia,  (q, per)),
    }

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {}
        for name, (cat, fn, args) in tasks.items():
            futures[pool.submit(fn, *args)] = (name, cat)
        for fut in as_completed(futures):
            name, cat = futures[fut]
            try:
                results = fut.result()
                if is_exact:
                    results = _filter_exact(results, q.lower())
                if results:
                    target = engines_out if cat == "engine" else crawlers_out
                    target[name] = results
            except Exception as e:
                errors.append(f"{name}: {e}")

    seen: set[str] = set()
    for bucket in (engines_out, crawlers_out):
        for name in list(bucket.keys()):
            bucket[name] = _dedup(bucket[name], seen)
            if not bucket[name]:
                del bucket[name]

    total = (sum(len(v) for v in engines_out.values())
             + sum(len(v) for v in crawlers_out.values()))

    return {
        "mode": "global_search",
        "query": raw_q,
        "exact_match": is_exact,
        "search_engines": engines_out,
        "crawlers": crawlers_out,
        "total": total,
        "errors": errors if errors else None,
    }
