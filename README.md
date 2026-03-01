# Spotify Playlist Finder

A small app that uses the **Spotify Web API** to find public playlists that contain your music and shows who owns each playlist (and location when available).

## What it does

- Searches Spotify for **your tracks** by artist name (and optionally track name).
- Searches for **playlists** that match your artist/track name.
- Checks each of those playlists for your tracks and lists every playlist that contains your music.
- For each match, shows: **playlist name**, **link**, **owner display name**, **owner ID**, and optionally **owner profile** (country is only exposed for the logged-in user on Spotify, so it often shows as “—” for other users).

## Spotify API access

You need a **Spotify app** and its **Client ID** and **Client Secret**. No user login is required (the app uses the **Client Credentials** flow for public data only).

### 1. Create an app in the Spotify Dashboard

1. Go to [Spotify for Developers](https://developer.spotify.com/).
2. Log in with your Spotify account.
3. Open the [Dashboard](https://developer.spotify.com/dashboard).
4. Click **Create app**.
5. Fill in:
   - **App name**: e.g. `Playlist Finder`
   - **App description**: e.g. `Find playlists that contain my music`
   - **Redirect URI**: not needed for Client Credentials; if you add user login later, use **https://localhost:8888/callback** (see [Secure localhost](#secure-localhost-https) below).
6. Accept the terms and create the app.

### 2. Get your credentials

1. Open your app in the Dashboard.
2. Click **Settings** (or view app details).
3. Copy **Client ID** and **Client Secret**.

### 3. Configure the app

1. In the project folder, copy the example env file:
   ```bash
   copy .env.example .env
   ```
2. Edit `.env` and set:
   ```env
   SPOTIFY_CLIENT_ID=your_client_id_here
   SPOTIFY_CLIENT_SECRET=your_client_secret_here
   ```
   Use the values from the Dashboard; do not commit `.env` or share these values.

## Setup and run

```bash
cd spotify-playlist-finder
pip install -r requirements.txt
python find_playlists.py "Your Artist Name"
```

### Web app

A browser UI is included. Start the server, then open the URL in your browser:

```bash
python app.py
```

Then open **http://127.0.0.1:5000**. You can search **by artist** or **by song** (track name, "Artist - Track", or Spotify track URL). Results show tracks, albums (for song search), playlists containing the music, and users who have it in a playlist. Optionally include a list of all checked playlist URLs.

### Examples (CLI)

```bash
# Search by artist name (finds your tracks, then playlists that contain them)
python find_playlists.py "Your Artist Name"

# Narrow to a specific track
python find_playlists.py "Your Artist Name" --track "Your Song Title"

# Check more playlists (default is 50)
python find_playlists.py "Your Artist Name" --max-playlists 100

# Try to fetch playlist owner public profile (country when available)
python find_playlists.py "Your Artist Name" --show-owner-profile

# Use a different market (country code)
python find_playlists.py "Your Artist Name" --market GB
```

## Limitations (Spotify API)

- **No “all playlists containing this track”**  
  The API does not let you query “every playlist that includes track X.” This app works by **searching playlists by keyword** (your artist/track name) and then **checking each playlist’s tracks**. So you only see playlists that show up in that search.

- **Location**  
  Listener location is not exposed. Playlist **owner** is available (display name, ID). **Country** is only returned for the **current user’s profile** in the API, not for other users’ public profiles, so “location” for playlist owners will often be “—” unless you add your own logic (e.g. user login and only for your own profile).

- **Public data only**  
  Using Client Credentials, you can only access **public** playlists and catalog data. Private playlists are not visible.

## Secure localhost (HTTPS)

If you use a redirect URI like `https://localhost:8888/callback` (for OAuth or a future web UI), run localhost over HTTPS so the browser doesn’t treat it as insecure.

### Option 1: Self-signed certificate (quick)

1. **Create a certificate and key** (one-time) in the project folder:
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
   ```
   (If you don’t have `openssl`, install [OpenSSL](https://slproweb.com/products/Win32OpenSSL.html) or use Git for Windows, which includes it.)

2. **Run the HTTPS server:**
   ```bash
   python serve_https.py
   ```
   Then open **https://localhost:8888** in your browser. You’ll get a warning because the cert is self-signed; choose “Advanced” → “Proceed to localhost” (or equivalent).

3. Add `key.pem` and `cert.pem` to `.gitignore` (they’re already listed in the script’s default paths; keep them private).

### Option 2: Trusted local cert with mkcert

For a cert your browser trusts without warnings:

1. Install [mkcert](https://github.com/FiloSottile/mkcert) and run `mkcert -install`.
2. In the project folder: `mkcert localhost 127.0.0.1` (creates `localhost+1.pem` and `localhost+1-key.pem`).
3. Run: `set SSL_CERT=localhost+1.pem& set SSL_KEY=localhost+1-key.pem& python serve_https.py` (Windows) or `SSL_CERT=localhost+1.pem SSL_KEY=localhost+1-key.pem python serve_https.py` (macOS/Linux).

In the Spotify Dashboard, set your redirect URI to **https://localhost:8888/callback** (not `http://`).

## Project structure

```
spotify-playlist-finder/
  .env.example    # Template for credentials
  requirements.txt
  spotify_client.py   # Spotify API client (auth + requests)
  find_playlists.py   # CLI: find playlists containing your music
  search_api.py       # API: run_artist_search / run_song_search (used by web app)
  app.py              # Web app (Flask)
  static/
    index.html        # Web UI
  serve_https.py       # Optional: HTTPS server for secure localhost
  README.md
```

## License

Use this code as you like. When using the Spotify API, you must follow [Spotify’s Developer Terms of Service](https://developer.spotify.com/terms) and [Design Guidelines](https://developer.spotify.com/documentation/design).
