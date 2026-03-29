"""
International search engines: Russia, China, Japan, South Korea, South America, Australia/NZ.
Uses DuckDuckGo with site: filters and direct API calls where available.
"""
import re
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


REGIONS = {
    "russia": {
        "label": "Russia",
        "flag": "\U0001F1F7\U0001F1FA",
        "engines": [
            {"name": "Yandex", "sites": ["yandex.ru", "yandex.com", "music.yandex.ru"]},
            {"name": "VK", "sites": ["vk.com"]},
            {"name": "Mail.ru", "sites": ["mail.ru", "my.mail.ru"]},
        ],
    },
    "china": {
        "label": "China",
        "flag": "\U0001F1E8\U0001F1F3",
        "engines": [
            {"name": "Baidu", "sites": ["baidu.com", "tieba.baidu.com"]},
            {"name": "Bilibili", "sites": ["bilibili.com"]},
            {"name": "Douban", "sites": ["douban.com", "music.douban.com"]},
            {"name": "NetEase Music", "sites": ["music.163.com"]},
            {"name": "QQ Music", "sites": ["y.qq.com"]},
        ],
    },
    "japan": {
        "label": "Japan",
        "flag": "\U0001F1EF\U0001F1F5",
        "engines": [
            {"name": "Yahoo Japan", "sites": ["yahoo.co.jp", "search.yahoo.co.jp"]},
            {"name": "Nico Nico", "sites": ["nicovideo.jp"]},
            {"name": "Hatena", "sites": ["hatena.ne.jp", "b.hatena.ne.jp"]},
            {"name": "Uta-Net", "sites": ["uta-net.com"]},
        ],
    },
    "korea": {
        "label": "South Korea",
        "flag": "\U0001F1F0\U0001F1F7",
        "engines": [
            {"name": "Naver", "sites": ["naver.com", "blog.naver.com", "cafe.naver.com"]},
            {"name": "Melon", "sites": ["melon.com"]},
            {"name": "Bugs", "sites": ["bugs.co.kr"]},
            {"name": "Daum/Kakao", "sites": ["daum.net"]},
        ],
    },
    "south_america": {
        "label": "South America",
        "flag": "\U0001F30E",
        "engines": [
            {"name": "Mercado Libre", "sites": ["mercadolibre.com", "mercadolibre.com.ar", "mercadolivre.com.br"]},
            {"name": "Letras.mus.br", "sites": ["letras.mus.br"]},
            {"name": "Vagalume", "sites": ["vagalume.com.br"]},
            {"name": "Rock.com.ar", "sites": ["rock.com.ar"]},
            {"name": "Terra", "sites": ["terra.com.br"]},
        ],
    },
    "oceania": {
        "label": "Australia & New Zealand",
        "flag": "\U0001F1E6\U0001F1FA",
        "engines": [
            {"name": "Triple J", "sites": ["abc.net.au/triplej", "abc.net.au"]},
            {"name": "NZ Herald", "sites": ["nzherald.co.nz"]},
            {"name": "Stuff.co.nz", "sites": ["stuff.co.nz"]},
            {"name": "Music Feeds", "sites": ["musicfeeds.com.au"]},
            {"name": "The Music AU", "sites": ["themusic.com.au"]},
            {"name": "Under The Radar NZ", "sites": ["undertheradar.co.nz"]},
        ],
    },
}


def _parse_quoted(s: str) -> tuple[str, bool]:
    s = (s or "").strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1].strip(), True
    return s, False


def run_intl_search(query: str, max_results: int = 50) -> dict[str, Any]:
    raw_q = (query or "").strip()
    if not raw_q:
        return {"error": "Search query is required"}
    q, is_exact = _parse_quoted(raw_q)
    if not q:
        return {"error": "Search query is required"}
    n = max(1, min(int(max_results), 100))

    region_results: dict[str, list[dict]] = {}
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(_search_region, region_key, q, n, is_exact): region_key
            for region_key in REGIONS
        }
        for fut in as_completed(futures):
            region_key = futures[fut]
            try:
                region_results[region_key] = fut.result()
            except Exception as e:
                errors.append(f"{region_key}: {e}")
                region_results[region_key] = []

    if is_exact:
        exact_lower = q.lower()
        for key in region_results:
            region_results[key] = [
                item for item in region_results[key]
                if exact_lower in (item.get("title") or "").lower()
                or exact_lower in (item.get("snippet") or "").lower()
            ]

    total = sum(len(v) for v in region_results.values())
    out: dict[str, Any] = {
        "mode": "international",
        "query": raw_q,
        "exact_match": is_exact,
        "total": total,
        "errors": errors if errors else None,
    }
    for key in REGIONS:
        out[key] = region_results.get(key, [])
    return out


def _search_region(region_key: str, query: str, max_results: int, exact: bool) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        return []

    region = REGIONS[region_key]
    all_sites: list[str] = []
    engine_names: list[str] = []
    for eng in region["engines"]:
        all_sites.extend(eng["sites"])
        engine_names.append(eng["name"])

    site_filter = " OR ".join(f"site:{s}" for s in all_sites)
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
        url = (r.get("href") or "")
        dedup_key = url.split("?")[0].split("#")[0].rstrip("/").lower()
        if not dedup_key or dedup_key in seen:
            continue
        seen.add(dedup_key)
        engine = _match_engine(url, region["engines"])
        out.append({
            "title": r.get("title") or "",
            "url": url,
            "snippet": (r.get("body") or "")[:600],
            "engine": engine,
            "region": region_key,
        })
    return out


def _match_engine(url: str, engines: list[dict]) -> str:
    url_lower = url.lower()
    for eng in engines:
        for site in eng["sites"]:
            if site in url_lower:
                return eng["name"]
    return ""
