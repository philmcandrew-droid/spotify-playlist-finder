"""
Spotify Web API client using Client Credentials flow.
No user login required — only needs app Client ID and Secret.
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.spotify.com/v1"
AUTH_URL = "https://accounts.spotify.com/api/token"


class SpotifyClient:
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self._token = None
        self._token_expires = 0

    def _get_token(self):
        if self._token and time.time() < self._token_expires:
            return self._token
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET. "
                "Copy .env.example to .env and add your credentials from "
                "https://developer.spotify.com/dashboard"
            )
        r = requests.post(
            AUTH_URL,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 3600) - 60
        return self._token

    def _headers(self):
        return {"Authorization": f"Bearer {self._get_token()}"}

    def search(self, q: str, type: str, limit: int = 10, offset: int = 0, market: str | None = None):
        """Search for playlists, tracks, or artists. Omit market to avoid 400 with client credentials."""
        params = {"q": q, "type": type, "limit": limit, "offset": offset}
        if market:
            params["market"] = market
        r = requests.get(f"{BASE_URL}/search", params=params, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def get_playlist(self, playlist_id: str, market: str = "US"):
        """Get playlist metadata (name, owner, etc.)."""
        r = requests.get(
            f"{BASE_URL}/playlists/{playlist_id}",
            params={"market": market},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def get_playlist_tracks(self, playlist_id: str, limit: int = 100, offset: int = 0, market: str = "US"):
        """Get tracks in a playlist (paginated)."""
        r = requests.get(
            f"{BASE_URL}/playlists/{playlist_id}/tracks",
            params={"limit": limit, "offset": offset, "market": market},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def get_track(self, track_id: str, market: str | None = None):
        """Get a single track by ID."""
        params = {}
        if market:
            params["market"] = market
        r = requests.get(f"{BASE_URL}/tracks/{track_id}", params=params or None, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def get_album(self, album_id: str, market: str | None = None):
        """Get a single album by ID."""
        params = {}
        if market:
            params["market"] = market
        r = requests.get(f"{BASE_URL}/albums/{album_id}", params=params or None, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def get_album_tracks(self, album_id: str, limit: int = 50, offset: int = 0, market: str | None = None):
        """Get tracks in an album (paginated)."""
        params = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market
        r = requests.get(f"{BASE_URL}/albums/{album_id}/tracks", params=params, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def get_all_album_tracks(self, album_id: str, market: str | None = None):
        """Fetch all tracks in an album, handling pagination."""
        out = []
        offset = 0
        limit = 50
        while True:
            data = self.get_album_tracks(album_id, limit=limit, offset=offset, market=market)
            items = data.get("items") or []
            out.extend(items)
            if not data.get("next"):
                break
            offset += limit
        return out

    def get_user_profile(self, user_id: str):
        """Get public profile of a user (display name, images). Country only for current user."""
        r = requests.get(f"{BASE_URL}/users/{user_id}", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def get_all_playlist_tracks(self, playlist_id: str, market: str = "US"):
        """Fetch all tracks in a playlist, handling pagination."""
        out = []
        offset = 0
        limit = 100
        while True:
            data = self.get_playlist_tracks(playlist_id, limit=limit, offset=offset, market=market)
            items = data.get("items") or []
            out.extend(items)
            if not data.get("next"):
                break
            offset += limit
        return out
