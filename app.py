"""
Web app for Spotify Playlist Finder.
Run: python app.py
Then open http://127.0.0.1:5000
"""
import os
from flask import Flask, send_from_directory, request, jsonify

from search_api import run_artist_search, run_song_search, run_album_search

app = Flask(__name__, static_folder="static", static_url_path="")


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


@app.route("/api/search-artist", methods=["POST"])
def api_search_artist():
    try:
        data = request.get_json() or {}
        artist = (data.get("artist") or "").strip()
        if not artist:
            return jsonify({"error": "Artist name is required"}), 400
        max_playlists = min(int(data.get("max_playlists") or 50), 200)
        track_name = (data.get("track") or "").strip() or None
        include_checked = bool(data.get("include_checked_playlists"))
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


@app.route("/api/search-song", methods=["POST"])
def api_search_song():
    try:
        data = request.get_json() or {}
        song = (data.get("song") or "").strip()
        if not song:
            return jsonify({"error": "Song query is required"}), 400
        max_playlists = min(int(data.get("max_playlists") or 50), 200)
        include_checked = bool(data.get("include_checked_playlists"))
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


@app.route("/api/search-album", methods=["POST"])
def api_search_album():
    try:
        data = request.get_json() or {}
        album = (data.get("album") or "").strip()
        if not album:
            return jsonify({"error": "Album query is required"}), 400
        max_playlists = min(int(data.get("max_playlists") or 50), 200)
        include_checked = bool(data.get("include_checked_playlists"))
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
