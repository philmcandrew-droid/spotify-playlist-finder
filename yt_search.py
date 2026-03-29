"""
YouTube search: official Data API v3 when YOUTUBE_API_KEY is set, else youtube-search (no key).
Module name avoids shadowing the youtube_search PyPI package.
"""
import os
from typing import Any

import requests


def run_youtube_search(query: str, max_results: int = 10) -> dict[str, Any]:
    """Return JSON-serializable dict with mode, query, videos[], and optional source."""
    q = (query or "").strip()
    if not q:
        return {"error": "Search query is required"}
    n = max(1, min(int(max_results), 100))

    api_key = (os.environ.get("YOUTUBE_API_KEY") or "").strip()
    if api_key:
        return _search_data_api(q, n, api_key)
    return _search_fallback(q, n)


def _search_data_api(query: str, max_results: int, api_key: str) -> dict[str, Any]:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=25)
    except requests.RequestException as e:
        return {"error": f"YouTube API request failed: {e}"}

    try:
        data = r.json()
    except ValueError:
        return {"error": "YouTube API returned invalid JSON"}

    if r.status_code != 200:
        err = (data.get("error") or {}) if isinstance(data, dict) else {}
        msg = err.get("message") or r.text or f"HTTP {r.status_code}"
        return {"error": f"YouTube API error: {msg}"}

    videos = []
    for item in (data.get("items") or []):
        vid_id = (item.get("id") or {}).get("videoId")
        sn = item.get("snippet") or {}
        if not vid_id:
            continue
        thumbs = sn.get("thumbnails") or {}
        thumb = (thumbs.get("medium") or thumbs.get("default") or {}) or {}
        videos.append({
            "title": sn.get("title") or "",
            "video_id": vid_id,
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "channel_title": sn.get("channelTitle") or "",
            "description": (sn.get("description") or "")[:500],
            "thumbnail": thumb.get("url") or "",
        })

    return {
        "mode": "youtube",
        "query": query,
        "source": "youtube_data_api",
        "videos": videos,
    }


def _search_fallback(query: str, max_results: int) -> dict[str, Any]:
    try:
        from youtube_search import YoutubeSearch
    except ImportError:
        return {
            "error": "YouTube search needs YOUTUBE_API_KEY in .env, or install: pip install youtube-search",
        }

    try:
        raw = YoutubeSearch(query, max_results=max_results).to_dict()
    except Exception as e:
        return {"error": f"YouTube search failed: {e}"}

    videos = []
    for row in raw or []:
        vid = row.get("id") or ""
        if not vid:
            continue
        thumbs = row.get("thumbnails") or []
        thumb = thumbs[0] if isinstance(thumbs, list) and thumbs else ""
        suffix = (row.get("url_suffix") or "").lstrip("/")
        if suffix.startswith("watch?v="):
            url = f"https://www.youtube.com/{suffix.split('&')[0]}"
        elif suffix.startswith("shorts/"):
            url = f"https://www.youtube.com/{suffix.split('?')[0]}"
        else:
            url = f"https://www.youtube.com/watch?v={vid}"
        videos.append({
            "title": row.get("title") or "",
            "video_id": vid,
            "url": url,
            "channel_title": row.get("channel") or "",
            "description": (row.get("long_desc") or "")[:500] if row.get("long_desc") else "",
            "thumbnail": thumb,
            "duration": row.get("duration"),
            "views": row.get("views"),
        })

    return {
        "mode": "youtube",
        "query": query,
        "source": "youtube_search",
        "videos": videos,
    }
