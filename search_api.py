"""
API-friendly search: run artist or song search and return JSON-serializable dict.
Used by the web app and any other API consumers.
"""
from spotify_client import SpotifyClient
from find_playlists import (
    parse_quoted,
    collect_your_track_and_artist_ids,
    find_song_references,
    find_album_references,
    _search_playlists_for_queries,
)


def _users_from_playlists(playlists_with_music: list) -> list:
    """Dedupe playlist owners into a list of unique users."""
    seen = {}
    for e in playlists_with_music:
        uid = e["owner_id"]
        if uid not in seen:
            seen[uid] = {
                "display_name": e["owner_display_name"],
                "id": uid,
                "profile_url": f"https://open.spotify.com/user/{uid}",
                "playlist_count": 0,
                "country": e.get("owner_country"),
                "followers": e.get("owner_followers"),
            }
        seen[uid]["playlist_count"] += 1
    return list(seen.values())


def run_artist_search(
    artist_name: str,
    max_playlists: int = 50,
    track_name: str | None = None,
    show_owner_profile: bool = False,
    include_checked_playlists: bool = False,
) -> dict:
    """Search by artist. Use \"quotes\" for exact phrase match. Returns a dict suitable for JSON."""
    client = SpotifyClient()
    artist_input = (artist_name or "").strip()
    if not artist_input:
        return {"error": "Artist name is required"}
    artist_name, is_exact = parse_quoted(artist_input)
    exact_phrase = artist_name if is_exact else None

    try:
        track_ids, artist_ids = collect_your_track_and_artist_ids(
            client, artist_name, track_name, exact_phrase=exact_phrase
        )
    except Exception as e:
        return {"error": str(e)}

    if not track_ids and not artist_ids:
        return {"error": "No tracks or artist found. Check the artist name."}

    search_queries = [artist_name]
    try:
        playlists_checked, playlists_with_music, all_checked = _search_playlists_for_queries(
            client, search_queries, track_ids, artist_ids, max_playlists, "US", show_owner_profile
        )
    except Exception as e:
        return {"error": str(e)}

    users = _users_from_playlists(playlists_with_music)
    out = {
        "mode": "artist",
        "query": artist_input,
        "exact_match": is_exact,
        "track_ids_count": len(track_ids),
        "artist_ids_count": len(artist_ids),
        "playlists_checked": playlists_checked,
        "playlists_with_music": playlists_with_music,
        "users": users,
        "track_infos": [],
        "album_infos": [],
    }
    if include_checked_playlists:
        out["all_checked_playlists"] = all_checked
    return out


def run_song_search(
    song_query: str,
    max_playlists: int = 50,
    show_owner_profile: bool = False,
    include_checked_playlists: bool = False,
) -> dict:
    """Search by song. Use \"quotes\" for exact phrase match. Returns a dict suitable for JSON."""
    client = SpotifyClient()
    song_input = (song_query or "").strip()
    if not song_input:
        return {"error": "Song query is required"}
    song_query, is_exact = parse_quoted(song_input)
    exact_phrase = song_query if is_exact else None

    try:
        track_ids, artist_ids, track_infos, album_infos = find_song_references(
            client, song_query, exact_phrase=exact_phrase
        )
    except Exception as e:
        return {"error": str(e)}

    if not track_ids and not artist_ids:
        return {"error": "No track found. Try a different search or a Spotify track URL."}

    search_queries = []
    for inf in track_infos[:3]:
        if inf.get("name"):
            search_queries.append(inf["name"])
        if inf.get("artists"):
            for part in (inf["artists"] or "").split(",")[:2]:
                p = part.strip()
                if p:
                    search_queries.append(p)
    search_queries = list(dict.fromkeys(search_queries))[:5]
    if not search_queries:
        search_queries = [song_query]

    try:
        playlists_checked, playlists_with_music, all_checked = _search_playlists_for_queries(
            client, search_queries, track_ids, artist_ids, max_playlists, "US", show_owner_profile
        )
    except Exception as e:
        return {"error": str(e)}

    users = _users_from_playlists(playlists_with_music)
    out = {
        "mode": "song",
        "query": song_input,
        "exact_match": is_exact,
        "track_infos": track_infos,
        "album_infos": album_infos,
        "playlists_checked": playlists_checked,
        "playlists_with_music": playlists_with_music,
        "users": users,
    }
    if include_checked_playlists:
        out["all_checked_playlists"] = all_checked
    return out


def run_album_search(
    album_query: str,
    max_playlists: int = 50,
    show_owner_profile: bool = False,
    include_checked_playlists: bool = False,
) -> dict:
    """Search by album. Use \"quotes\" for exact phrase match. Returns a dict suitable for JSON."""
    client = SpotifyClient()
    album_input = (album_query or "").strip()
    if not album_input:
        return {"error": "Album query is required"}
    album_query, is_exact = parse_quoted(album_input)
    exact_phrase = album_query if is_exact else None

    try:
        track_ids, artist_ids, track_infos, album_infos = find_album_references(
            client, album_query, exact_phrase=exact_phrase
        )
    except Exception as e:
        return {"error": str(e)}

    if not track_ids and not artist_ids:
        return {"error": "No album or tracks found. Check the album name or try a Spotify album URL."}

    search_queries = []
    for a in album_infos[:3]:
        if a.get("name"):
            search_queries.append(a["name"])
        if a.get("artist"):
            for part in (a["artist"] or "").split(",")[:2]:
                p = part.strip()
                if p:
                    search_queries.append(p)
    search_queries = list(dict.fromkeys(search_queries))[:5]
    if not search_queries:
        search_queries = [album_query]

    try:
        playlists_checked, playlists_with_music, all_checked = _search_playlists_for_queries(
            client, search_queries, track_ids, artist_ids, max_playlists, "US", show_owner_profile
        )
    except Exception as e:
        return {"error": str(e)}

    users = _users_from_playlists(playlists_with_music)
    out = {
        "mode": "album",
        "query": album_input,
        "exact_match": is_exact,
        "track_infos": track_infos,
        "album_infos": album_infos,
        "playlists_checked": playlists_checked,
        "playlists_with_music": playlists_with_music,
        "users": users,
    }
    if include_checked_playlists:
        out["all_checked_playlists"] = all_checked
    return out
