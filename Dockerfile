# Production image for Spotify Playlist Finder (Flask + Gunicorn)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py search_api.py spotify_client.py find_playlists.py yt_search.py deep_search.py social_search.py intl_search.py global_search.py ./
COPY static ./static/

EXPOSE 5000

# Hosts set PORT (Render, Fly, Railway, etc.); default 5000
CMD exec gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 app:app
