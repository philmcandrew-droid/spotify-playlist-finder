"""
Find users who have your song (in a playlist) and the playlists that contain your tracks.
Find any reference to any song on Spotify: track, albums, playlists, users.

Note: Spotify's API does not expose "users who saved this track to their library".
We can only find users who added your track to a public playlist (playlist owners).

Usage:
  # By artist (your music)
  python find_playlists.py "Your Artist Name"
  python find_playlists.py "Your Artist Name" --track "Song Title"

  # Any song on Spotify (find all references)
  python find_playlists.py --song "Blinding Lights"
  python find_playlists.py --song "The Weeknd - Blinding Lights"
  python find_playlists.py --song "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b"

  python find_playlists.py "Your Artist Name" --max-playlists 100
  python find_playlists.py "Your Artist Name" --users-only   # list only unique users

Requires .env with SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.
"""

import argparse
import re
import sys
from spotify_client import SpotifyClient


def parse_quoted(s: str) -> tuple[str, bool]:
    """
    If s is wrapped in double quotes, return (inner_stripped, True) for exact match.
    Otherwise return (stripped, False).
    """
    s = (s or "").strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1].strip(), True
    return s, False


def extract_track_id(s: str) -> str | None:
    """Extract Spotify track ID from URL or URI. Returns None if not found."""
    s = (s or "").strip()
    # spotify:track:xxx or https://open.spotify.com/track/xxx
    m = re.search(r"(?:spotify:track:|/track/)([a-zA-Z0-9]{22})", s)
    return m.group(1) if m else None


def extract_album_id(s: str) -> str | None:
    """Extract Spotify album ID from URL or URI. Returns None if not found."""
    s = (s or "").strip()
    m = re.search(r"(?:spotify:album:|/album/)([a-zA-Z0-9]{22})", s)
    return m.group(1) if m else None


def find_song_references(
    client: SpotifyClient,
    song_query: str,
    exact_phrase: str | None = None,
) -> tuple[set[str], set[str], list[dict], list[dict]]:
    """
    Find a song on Spotify by name, "Artist - Track", or track URL/ID.
    If exact_phrase is set, only keep tracks that exactly match (track name or artists).
    Returns (track_ids, artist_ids, track_infos, album_infos) for reporting.
    """
    track_ids = set()
    artist_ids = set()
    track_infos = []  # {"name", "url", "id", "artists": "A, B"}
    album_infos = []  # {"name", "url", "id", "artist"}

    # Try as Spotify track URL or ID first
    tid = extract_track_id(song_query)
    if tid:
        try:
            t = client.get_track(tid)
            track_ids.add(t["id"])
            artists = t.get("artists") or []
            for a in artists:
                artist_ids.add(a["id"])
            track_infos.append({
                "name": t.get("name"),
                "url": (t.get("external_urls") or {}).get("spotify") or f"https://open.spotify.com/track/{t['id']}",
                "id": t["id"],
                "artists": ", ".join(a.get("name", "?") for a in artists),
            })
            album = t.get("album")
            if album and album.get("id"):
                album_infos.append({
                    "name": album.get("name"),
                    "url": (album.get("external_urls") or {}).get("spotify") or f"https://open.spotify.com/album/{album['id']}",
                    "id": album["id"],
                    "artist": ", ".join(a.get("name", "?") for a in (album.get("artists") or [])),
                })
            if exact_phrase:
                match_key = exact_phrase.strip().lower()
                track_infos = [t for t in track_infos if (t.get("name") or "").strip().lower() == match_key or (t.get("artists") or "").strip().lower() == match_key]
                track_ids = {t["id"] for t in track_infos}
            return track_ids, artist_ids, track_infos, album_infos
        except Exception as e:
            print(f"Track ID lookup error: {e}", file=sys.stderr)

    # Search by text: "Artist - Track" or just "Track Name"
    search_query = song_query.strip()
    parts = [p.strip() for p in search_query.split(" - ", 1)]
    if len(parts) == 2 and parts[0] and parts[1]:
        search_q = search_query
    else:
        search_q = search_query

    try:
        result = client.search(search_q, type="track", limit=10)
    except Exception as e:
        print(f"Track search error: {e}", file=sys.stderr)
        return track_ids, artist_ids, track_infos, album_infos

    tracks = result.get("tracks", {}).get("items") or []
    for t in tracks:
        if not t or t.get("type") != "track":
            continue
        artists = t.get("artists") or []
        artist_names = ", ".join(a.get("name", "?") for a in artists)
        if exact_phrase:
            match_key = exact_phrase.strip().lower()
            name_ok = (t.get("name") or "").strip().lower() == match_key
            artists_ok = artist_names.strip().lower() == match_key
            if not name_ok and not artists_ok:
                continue
        track_ids.add(t["id"])
        for a in artists:
            artist_ids.add(a["id"])
        track_infos.append({
            "name": t.get("name"),
            "url": (t.get("external_urls") or {}).get("spotify") or f"https://open.spotify.com/track/{t['id']}",
            "id": t["id"],
            "artists": artist_names,
        })
        album = t.get("album")
        if album and album.get("id") and not any(al.get("id") == album.get("id") for al in album_infos):
            album_infos.append({
                "name": album.get("name"),
                "url": (album.get("external_urls") or {}).get("spotify") or f"https://open.spotify.com/album/{album['id']}",
                "id": album["id"],
                "artist": ", ".join(a.get("name", "?") for a in (album.get("artists") or [])),
            })
    return track_ids, artist_ids, track_infos, album_infos


def find_album_references(
    client: SpotifyClient,
    album_query: str,
    exact_phrase: str | None = None,
) -> tuple[set[str], set[str], list[dict], list[dict]]:
    """
    Find an album on Spotify by name, "Artist - Album", or album URL/ID.
    If exact_phrase is set, only keep albums whose name exactly matches (case-insensitive).
    Returns (track_ids, artist_ids, track_infos, album_infos) for reporting.
    """
    track_ids = set()
    artist_ids = set()
    track_infos = []
    album_infos = []

    # Try as Spotify album URL or ID first
    aid = extract_album_id(album_query)
    if aid:
        try:
            album = client.get_album(aid)
            album_name = album.get("name")
            album_artists = ", ".join(a.get("name", "?") for a in (album.get("artists") or []))
            album_infos.append({
                "name": album_name,
                "url": (album.get("external_urls") or {}).get("spotify") or f"https://open.spotify.com/album/{album['id']}",
                "id": album["id"],
                "artist": album_artists,
            })
            for item in client.get_all_album_tracks(album["id"]):
                if not item or not item.get("id"):
                    continue
                track_ids.add(item["id"])
                artists = item.get("artists") or []
                for a in artists:
                    artist_ids.add(a["id"])
                track_infos.append({
                    "name": item.get("name"),
                    "url": f"https://open.spotify.com/track/{item['id']}",
                    "id": item["id"],
                    "artists": ", ".join(a.get("name", "?") for a in artists),
                })
            return track_ids, artist_ids, track_infos, album_infos
        except Exception as e:
            print(f"Album lookup error: {e}", file=sys.stderr)

    # Search by text
    search_q = album_query.strip()
    try:
        result = client.search(search_q, type="album", limit=10)
    except Exception as e:
        print(f"Album search error: {e}", file=sys.stderr)
        return track_ids, artist_ids, track_infos, album_infos

    albums = result.get("albums", {}).get("items") or []
    for alb in albums:
        if not alb or alb.get("type") != "album":
            continue
        if exact_phrase and (alb.get("name") or "").strip().lower() != exact_phrase.strip().lower():
            continue
        album_id = alb.get("id")
        if not album_id:
            continue
        if any(a.get("id") == album_id for a in album_infos):
            continue
        album_infos.append({
            "name": alb.get("name"),
            "url": (alb.get("external_urls") or {}).get("spotify") or f"https://open.spotify.com/album/{album_id}",
            "id": album_id,
            "artist": ", ".join(a.get("name", "?") for a in (alb.get("artists") or [])),
        })
        try:
            for item in client.get_all_album_tracks(album_id):
                if not item or not item.get("id"):
                    continue
                track_ids.add(item["id"])
                artists = item.get("artists") or []
                for a in artists:
                    artist_ids.add(a["id"])
                track_infos.append({
                    "name": item.get("name"),
                    "url": f"https://open.spotify.com/track/{item['id']}",
                    "id": item["id"],
                    "artists": ", ".join(a.get("name", "?") for a in artists),
                })
        except Exception:
            continue
    return track_ids, artist_ids, track_infos, album_infos


def collect_your_track_and_artist_ids(
    client: SpotifyClient,
    artist_name: str,
    track_name: str | None,
    exact_phrase: str | None = None,
):
    """Search for your tracks/artist and return sets of track IDs and artist IDs to match.
    If exact_phrase is set, only include artists whose name exactly matches (case-insensitive)."""
    # Spotify search: use plain phrase (exact match is enforced by filtering below)
    search_q = artist_name
    artist_ids = set()
    try:
        art_result = client.search(search_q, type="artist", limit=10)
        for a in (art_result.get("artists") or {}).get("items") or []:
            name = (a.get("name") or "").strip()
            if exact_phrase and name.lower() != exact_phrase.strip().lower():
                continue
            artist_ids.add(a["id"])
    except Exception as e:
        print(f"Artist search error: {e}", file=sys.stderr)

    q = search_q if not track_name else f"{search_q} {track_name}"
    track_ids = set()
    try:
        result = client.search(q, type="track", limit=10)
        tracks = result.get("tracks", {}).get("items") or []
        match_key = exact_phrase.strip().lower() if exact_phrase else None
        for t in tracks:
            if not t or t.get("type") != "track":
                continue
            track_artist_ids = {a["id"] for a in (t.get("artists") or [])}
            if exact_phrase:
                artist_names = [a.get("name", "") for a in (t.get("artists") or [])]
                if not any((n or "").strip().lower() == match_key for n in artist_names):
                    continue
            elif artist_ids and track_artist_ids.isdisjoint(artist_ids):
                continue
            track_ids.add(t["id"])
            artist_ids.update(track_artist_ids)
    except Exception as e:
        print(f"Track search error: {e}", file=sys.stderr)

    return track_ids, artist_ids


def playlist_contains_your_music(client: SpotifyClient, playlist_id: str, track_ids: set, artist_ids: set, market: str = "US"):
    """Return (True, list of matching track names) if playlist contains any of your tracks."""
    try:
        items = client.get_all_playlist_tracks(playlist_id, market=market)
    except Exception:
        return False, []

    matches = []
    for item in items:
        track = (item or {}).get("track")
        if not track or track.get("type") != "track" or not track.get("id"):
            continue
        if track["id"] in track_ids:
            matches.append(track.get("name") or "?")
            continue
        for a in (track.get("artists") or []):
            if a.get("id") in artist_ids:
                matches.append(track.get("name") or "?")
                break
    return len(matches) > 0, matches


def _search_playlists_for_queries(
    client: SpotifyClient,
    search_queries: list[str],
    track_ids: set,
    artist_ids: set,
    max_playlists: int,
    market: str,
    show_owner_profile: bool,
) -> tuple[int, list, list[dict]]:
    """Search playlists with multiple queries, dedupe by playlist ID, check for track. Returns (checked_count, playlists_with_music, all_checked_playlists)."""
    seen_pl_ids = set()
    playlists_to_check = []  # list of (pl_id, pl_obj)
    limit = 10
    for q in search_queries:
        if len(playlists_to_check) >= max_playlists:
            break
        offset = 0
        while len(playlists_to_check) < max_playlists:
            try:
                result = client.search(q, type="playlist", limit=limit, offset=offset)
            except Exception as e:
                print(f"Playlist search error for '{q}': {e}", file=sys.stderr)
                break
            playlists = (result.get("playlists") or {}).get("items") or []
            if not playlists:
                break
            for pl in playlists:
                pl_id = (pl or {}).get("id")
                if pl_id and pl_id not in seen_pl_ids:
                    seen_pl_ids.add(pl_id)
                    playlists_to_check.append((pl_id, pl))
                if len(playlists_to_check) >= max_playlists:
                    break
            if not result.get("playlists", {}).get("next"):
                break
            offset += limit
        if len(playlists_to_check) >= max_playlists:
            break

    playlists_with_your_music = []
    for pl_id, pl in playlists_to_check:
        contains, match_names = playlist_contains_your_music(client, pl_id, track_ids, artist_ids, market)
        if contains:
            owner = (pl.get("owner") or {})
            owner_id = owner.get("id") or "?"
            owner_display = owner.get("display_name") or owner_id
            entry = {
                "name": pl.get("name") or "?",
                "id": pl_id,
                "url": pl.get("external_urls", {}).get("spotify") or f"https://open.spotify.com/playlist/{pl_id}",
                "owner_display_name": owner_display,
                "owner_id": owner_id,
                "tracks_found": match_names,
            }
            if show_owner_profile:
                try:
                    profile = client.get_user_profile(owner_id)
                    entry["owner_country"] = profile.get("country") or "—"
                    entry["owner_followers"] = profile.get("followers", {}).get("total")
                except Exception:
                    entry["owner_country"] = "—"
                    entry["owner_followers"] = None
            playlists_with_your_music.append(entry)
    all_checked = [
        {"name": pl.get("name") or "?", "url": pl.get("external_urls", {}).get("spotify") or f"https://open.spotify.com/playlist/{pl_id}"}
        for pl_id, pl in playlists_to_check
    ]
    return len(playlists_to_check), playlists_with_your_music, all_checked


def main():
    parser = argparse.ArgumentParser(description="Find Spotify playlists that contain your music, or find any reference to any song")
    parser.add_argument("artist", nargs="?", default=None, help="Artist name (optional if using --song)")
    parser.add_argument("--artist", dest="artist_opt", default=None, help="Artist name (same as positional)")
    parser.add_argument("--song", default=None, help="Find any reference to this song: track name, 'Artist - Track', or Spotify track URL")
    parser.add_argument("--track", default=None, help="Optional: limit to a specific track name (when using artist)")
    parser.add_argument("--max-playlists", type=int, default=50, help="Max number of playlists to check (default 50)")
    parser.add_argument("--market", default="US", help="Market/country code (default US)")
    parser.add_argument("--show-owner-profile", action="store_true", help="Fetch playlist owner public profile (slower)")
    parser.add_argument("--users-only", action="store_true", help="Print only the list of unique users who have your song")
    parser.add_argument("--show-checked-playlists", action="store_true", help="Print name and URL of every playlist checked")
    args = parser.parse_args()

    client = SpotifyClient()
    song_mode = bool(args.song and args.song.strip())

    if song_mode:
        # --- Find any reference to any song ---
        song_query_raw = args.song.strip()
        song_query, is_exact = parse_quoted(song_query_raw)
        exact_phrase = song_query if is_exact else None
        print(f"Finding all references to: {song_query_raw!r}{' (exact match)' if is_exact else ''}...")
        track_ids, artist_ids, track_infos, album_infos = find_song_references(client, song_query, exact_phrase=exact_phrase)
        if not track_ids and not artist_ids:
            print("No track found. Try a different search or a Spotify track URL.", file=sys.stderr)
            sys.exit(1)
        # Build playlist search queries (exact match enforced by filtering)
        search_queries = []
        for inf in track_infos[:3]:
            if inf.get("name"):
                search_queries.append(inf["name"])
            if inf.get("artists"):
                for part in inf["artists"].split(",")[:2]:
                    p = part.strip()
                    if p:
                        search_queries.append(p)
        search_queries = list(dict.fromkeys(search_queries))[:5]
        if not search_queries:
            search_queries = [song_query]
        print(f"  Track(s): {len(track_ids)}, Artist(s): {len(artist_ids)}")
        print(f"  Searching playlists for: {', '.join(search_queries[:3])}... (max {args.max_playlists} playlists)")
        playlists_checked, playlists_with_your_music, all_checked_playlists = _search_playlists_for_queries(
            client, search_queries, track_ids, artist_ids, args.max_playlists, args.market, args.show_owner_profile
        )
    else:
        # --- By artist (original flow) ---
        artist_input = (args.artist_opt or args.artist or "").strip()
        if not artist_input:
            print("Provide an artist name or use --song \"Track Name\" to find any song.", file=sys.stderr)
            sys.exit(1)
        artist_name, is_exact = parse_quoted(artist_input)
        exact_phrase = artist_name if is_exact else None
        print(f"Finding your tracks/artist on Spotify (artist: {artist_input!r}{' [exact match]' if is_exact else ''})...")
        track_ids, artist_ids = collect_your_track_and_artist_ids(client, artist_name, args.track, exact_phrase=exact_phrase)
        if not track_ids and not artist_ids:
            print("No tracks or artist found. Check the artist name and try again.", file=sys.stderr)
            sys.exit(1)
        print(f"  Your artist/track IDs collected: {len(track_ids)} track(s), {len(artist_ids)} artist(s)")
        track_infos = []
        album_infos = []
        search_queries = [artist_name]
        print(f"\nSearching playlists for: {search_queries[0]} (max {args.max_playlists} playlists)...")
        playlists_checked, playlists_with_your_music, all_checked_playlists = _search_playlists_for_queries(
            client, search_queries, track_ids, artist_ids, args.max_playlists, args.market, args.show_owner_profile
        )

    # Unique users

    # Unique users (playlist owners who have your song)
    users_seen = {}
    for e in playlists_with_your_music:
        uid = e["owner_id"]
        if uid not in users_seen:
            users_seen[uid] = {
                "display_name": e["owner_display_name"],
                "id": uid,
                "profile_url": f"https://open.spotify.com/user/{uid}",
                "playlist_count": 0,
                "owner_country": e.get("owner_country"),
                "owner_followers": e.get("owner_followers"),
            }
        users_seen[uid]["playlist_count"] += 1

    # Report
    if song_mode and (track_infos or album_infos):
        print("\n--- References to this song on Spotify ---\n")
        if track_infos:
            print("  Track(s):")
            for t in track_infos:
                print(f"    • {t.get('name', '?')} — {t.get('artists', '?')}")
                print(f"      {t.get('url', '')}")
            print()
        if album_infos:
            print("  Album(s) this track appears on:")
            for a in album_infos:
                print(f"    • {a.get('name', '?')} — {a.get('artist', '?')}")
                print(f"      {a.get('url', '')}")
            print()

    print(f"Checked {playlists_checked} playlist(s). Found {len(playlists_with_your_music)} playlist(s) containing this music.")
    print(f"Unique users who have this song (in a playlist): {len(users_seen)}\n")

    if args.users_only:
        print("--- Users who have your song ---\n")
        for u in users_seen.values():
            print(f"  • {u['display_name']}")
            print(f"    Profile: {u['profile_url']}")
            print(f"    User ID: {u['id']}")
            print(f"    Playlists containing your music: {u['playlist_count']}")
            if u.get("owner_country") is not None:
                print(f"    Country: {u.get('owner_country', '—')}")
            if u.get("owner_followers") is not None:
                print(f"    Followers: {u['owner_followers']}")
            print()
        return

    print("--- Users who have your song ---\n")
    for u in users_seen.values():
        print(f"  • {u['display_name']} (ID: {u['id']}) — {u['playlist_count']} playlist(s) — {u['profile_url']}")
    print("\n--- Playlists ---\n")
    for e in playlists_with_your_music:
        print(f"  • {e['name']}")
        print(f"    Playlist: {e['url']}")
        print(f"    Owner: {e['owner_display_name']} (ID: {e['owner_id']})")
        if e.get("owner_country") is not None:
            print(f"    Country: {e.get('owner_country', '—')}")
        if e.get("owner_followers") is not None:
            print(f"    Followers: {e['owner_followers']}")
        print(f"    Your track(s) in playlist: {', '.join(e['tracks_found'][:10])}{' ...' if len(e['tracks_found']) > 10 else ''}")
        print()

    if args.show_checked_playlists and all_checked_playlists:
        print("--- All checked playlists (URLs) ---\n")
        for i, p in enumerate(all_checked_playlists, 1):
            # Avoid Windows console encoding errors on special characters
            name = (p["name"] or "?").encode("ascii", errors="replace").decode("ascii")
            print(f"  {i}. {name}")
            print(f"     {p['url']}")
        print()

if __name__ == "__main__":
    main()
