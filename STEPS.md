# Steps to run the Spotify Playlist Finder

Follow these in order.

---

## Step 1: Get Spotify API credentials

1. Go to **[developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)** and log in with your Spotify account.
2. Click **Create app**.
3. Fill in:
   - **App name:** e.g. `Playlist Finder`
   - **App description:** e.g. `Find playlists that contain my music`
   - **Redirect URI:** leave as-is or use **https://localhost:8888/callback** (see “Secure localhost” section below if you need HTTPS)
4. Check the box to agree to the terms and click **Save**.
5. Open your new app and click **Settings** (or view app details).
6. Copy your **Client ID** and **Client Secret** (click **Show client secret** if needed). Keep these private.

**Secure localhost:** Use **https://localhost:8888/callback** (not `http://`) so the redirect URI is secure. See the README section “Secure localhost (HTTPS)” for how to run a local HTTPS server and create a self-signed cert.

---

## Step 2: Create your `.env` file

1. Open the project folder: `c:\Users\philm\.cursor\spotify-playlist-finder`
2. Copy the example env file:
   - **PowerShell:** `Copy-Item .env.example .env`
   - **Or:** duplicate `.env.example` and rename the copy to `.env`
3. Open `.env` in a text editor.
4. Replace the placeholders with your real values:
   ```
   SPOTIFY_CLIENT_ID=paste_your_client_id_here
   SPOTIFY_CLIENT_SECRET=paste_your_client_secret_here
   ```
5. Save the file. Do not share `.env` or commit it to git.

---

## Step 3: Install Python (if not already installed)

1. Open **Microsoft Store** and search for **Python 3.12**, then install it.  
   **Or** download from **[python.org/downloads](https://www.python.org/downloads/)** and during setup **check "Add Python to PATH"**.
2. Open a **new** terminal (or restart Cursor) so Python is on your PATH.

---

## Step 4: Install project dependencies

1. Open a terminal (PowerShell or Command Prompt).
2. Go to the project folder:
   ```powershell
   cd c:\Users\philm\.cursor\spotify-playlist-finder
   ```
3. Install the required packages:
   ```powershell
   pip install -r requirements.txt
   ```

---

## Step 5: Run the playlist finder

1. In the same terminal, run (using your artist name):
   ```powershell
   python find_playlists.py "phil mcandrew"
   ```
2. The script will:
   - Find your tracks on Spotify
   - Search for playlists that match your artist name
   - List each playlist that contains your music, with owner and link

---

## Optional: use different options

- Search by artist and track:
  ```powershell
  python find_playlists.py "phil mcandrew" --track "Your Song Title"
  ```
- Check more playlists (default is 50):
  ```powershell
  python find_playlists.py "phil mcandrew" --max-playlists 100
  ```
- Try to show playlist owner profile info:
  ```powershell
  python find_playlists.py "phil mcandrew" --show-owner-profile
  ```

---

## Troubleshooting

| Problem | What to do |
|--------|------------|
| `Python was not found` | Install Python (Step 3) and use a **new** terminal. |
| `Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET` | Complete Step 1 and Step 2; make sure `.env` is in the project folder and has no typos. |
| `No tracks or artist found` | Check your artist name spelling and that your music is on Spotify. |
| `401` or `403` from API | Confirm Client ID and Secret are correct and the app is active in the Spotify Dashboard. |
