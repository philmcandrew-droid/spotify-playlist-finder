"""
Web app for Spotify Playlist Finder.
Run: python app.py
Then open http://127.0.0.1:5000
"""
import os
from flask import Flask, send_from_directory, request, jsonify

from search_api import run_artist_search, run_song_search, run_album_search
from yt_search import run_youtube_search
from deep_search import run_deep_search
from social_search import run_social_search
from intl_search import run_intl_search
from global_search import run_global_search

# Must not use static_url_path="" — Flask adds /<path:filename> for static files, which
# matches /api/... and only allows GET/HEAD, so POST /api/search-* returns 405.
app = Flask(__name__, static_folder="static", static_url_path="/static")


def _request_payload() -> dict:
    """JSON body for POST; query string for GET (avoids 405 when opening /api/... in a browser)."""
    if request.method == "POST":
        return request.get_json(silent=True) or {}
    return request.args.to_dict(flat=True)


def _bool_param(data: dict, key: str, default: bool = False) -> bool:
    """Query strings are always str; JSON may send real bools."""
    v = data.get(key)
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("0", "false", "no", "off", ""):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return default


def _int_param(data: dict, key: str, default: int, lo: int | None = None, hi: int | None = None) -> int:
    try:
        n = int(data.get(key) if data.get(key) not in (None, "") else default)
    except (TypeError, ValueError):
        n = default
    if lo is not None:
        n = max(lo, n)
    if hi is not None:
        n = min(hi, n)
    return n


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(_e):
    return jsonify({"error": "Internal server error"}), 500


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/search-artist", methods=["GET", "POST"])
def api_search_artist():
    try:
        data = _request_payload()
        artist = (data.get("artist") or "").strip()
        if not artist:
            return jsonify({"error": "Artist name is required"}), 400
        max_playlists = _int_param(data, "max_playlists", 50, lo=10, hi=200)
        track_name = (data.get("track") or "").strip() or None
        include_checked = _bool_param(data, "include_checked_playlists")
        result = run_artist_search(
            artist_name=artist,
            max_playlists=max_playlists,
            track_name=track_name,
            show_owner_profile=False,
            include_checked_playlists=include_checked,
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search-song", methods=["GET", "POST"])
def api_search_song():
    try:
        data = _request_payload()
        song = (data.get("song") or "").strip()
        if not song:
            return jsonify({"error": "Song query is required"}), 400
        max_playlists = _int_param(data, "max_playlists", 50, lo=10, hi=200)
        include_checked = _bool_param(data, "include_checked_playlists")
        result = run_song_search(
            song_query=song,
            max_playlists=max_playlists,
            show_owner_profile=False,
            include_checked_playlists=include_checked,
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search-youtube", methods=["GET", "POST"])
def api_search_youtube():
    try:
        data = _request_payload()
        q = (data.get("query") or "").strip()
        if not q:
            return jsonify({"error": "Search query is required"}), 400
        max_results = _int_param(data, "max_results", 10, lo=1, hi=100)
        result = run_youtube_search(query=q, max_results=max_results)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/deep-search", methods=["GET", "POST"])
def api_deep_search():
    try:
        data = _request_payload()
        q = (data.get("query") or "").strip()
        if not q:
            return jsonify({"error": "Search query is required"}), 400
        max_results = _int_param(data, "max_results", 25, lo=1, hi=100)
        result = run_deep_search(query=q, max_results=max_results)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search-social", methods=["GET", "POST"])
def api_search_social():
    try:
        data = _request_payload()
        q = (data.get("query") or "").strip()
        if not q:
            return jsonify({"error": "Search query is required"}), 400
        max_results = _int_param(data, "max_results", 25, lo=1, hi=100)
        result = run_social_search(query=q, max_results=max_results)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search-international", methods=["GET", "POST"])
def api_search_international():
    try:
        data = _request_payload()
        q = (data.get("query") or "").strip()
        if not q:
            return jsonify({"error": "Search query is required"}), 400
        max_results = _int_param(data, "max_results", 50, lo=1, hi=100)
        result = run_intl_search(query=q, max_results=max_results)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search-global", methods=["GET", "POST"])
def api_search_global():
    try:
        data = _request_payload()
        q = (data.get("query") or "").strip()
        if not q:
            return jsonify({"error": "Search query is required"}), 400
        max_results = _int_param(data, "max_results", 50, lo=1, hi=100)
        result = run_global_search(query=q, max_results=max_results)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search-album", methods=["GET", "POST"])
def api_search_album():
    try:
        data = _request_payload()
        album = (data.get("album") or "").strip()
        if not album:
            return jsonify({"error": "Album query is required"}), 400
        max_playlists = _int_param(data, "max_playlists", 50, lo=10, hi=200)
        include_checked = _bool_param(data, "include_checked_playlists")
        result = run_album_search(
            album_query=album,
            max_playlists=max_playlists,
            show_owner_profile=False,
            include_checked_playlists=include_checked,
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
