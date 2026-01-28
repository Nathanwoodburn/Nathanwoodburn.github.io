from flask import redirect, request, Blueprint, url_for
from tools import json_response
import os
import requests
import time
import base64

app = Blueprint("spotify", __name__, url_prefix="/spotify")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
ALLOWED_SPOTIFY_USER_ID = os.getenv("SPOTIFY_USER_ID")

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"


SCOPE = "user-read-currently-playing user-read-playback-state user-read-recently-played"

ACCESS_TOKEN = None
REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")
TOKEN_EXPIRES = 0


def refresh_access_token():
    """Refresh Spotify access token when expired."""
    global ACCESS_TOKEN, TOKEN_EXPIRES

    # If no refresh token, cannot proceed
    if not REFRESH_TOKEN:
        return None

    # If still valid, reuse it
    if ACCESS_TOKEN and time.time() < TOKEN_EXPIRES - 60:
        return ACCESS_TOKEN

    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
    }
    headers = {"Authorization": f"Basic {b64_auth}"}

    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    if response.status_code != 200:
        print("Failed to refresh token:", response.text)
        return None

    token_info = response.json()
    ACCESS_TOKEN = token_info["access_token"]
    TOKEN_EXPIRES = time.time() + token_info.get("expires_in", 3600)
    return ACCESS_TOKEN


@app.route("/login")
def login():
    auth_query = (
        f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={url_for('spotify.callback', _external=True)}&scope={SCOPE}"
    )
    return redirect(auth_query)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Authorization failed.", 400

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": url_for("spotify.callback", _external=True),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(SPOTIFY_TOKEN_URL, data=data)
    token_info = response.json()
    if "access_token" not in token_info:
        return json_response(
            request, {"error": "Failed to obtain token", "details": token_info}, 400
        )

    access_token = token_info["access_token"]
    me = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    if me.get("id") != ALLOWED_SPOTIFY_USER_ID:
        return json_response(request, {"error": "Unauthorized user"}, 403)

    global REFRESH_TOKEN
    REFRESH_TOKEN = token_info.get("refresh_token")
    print("Spotify authorization successful.")
    print("Refresh Token:", REFRESH_TOKEN)
    return redirect(url_for("spotify.currently_playing"))


@app.route("/", strict_slashes=False)
@app.route("/playing")
def currently_playing():
    """Public endpoint showing your current track."""
    track = get_playing_spotify_track()
    return json_response(request, {"spotify": track}, 200)


def get_playing_spotify_track():
    """Internal function to get current playing track without HTTP context."""
    token = refresh_access_token()
    if not token:
        return {"error": "Failed to refresh access token"}

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(SPOTIFY_CURRENTLY_PLAYING_URL, headers=headers)
    if response.status_code == 204:
        # return {"error": "Nothing is currently playing."}
        return get_last_spotify_track()
    elif response.status_code != 200:
        return {"error": "Spotify API error", "status": response.status_code}

    data = response.json()
    if not data.get("item"):
        return {"error": "Nothing is currently playing."}

    track = {
        "song_name": data["item"]["name"],
        "artist": ", ".join([artist["name"] for artist in data["item"]["artists"]]),
        "album_name": data["item"]["album"]["name"],
        "album_art": data["item"]["album"]["images"][0]["url"],
        "is_playing": data["is_playing"],
        "progress_ms": data.get("progress_ms", 0),
        "duration_ms": data["item"].get("duration_ms", 1),
    }
    return track


def get_last_spotify_track():
    """Internal function to get last played track without HTTP context."""
    token = refresh_access_token()
    if not token:
        return {"error": "Failed to refresh access token"}

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        "https://api.spotify.com/v1/me/player/recently-played", headers=headers
    )
    if response.status_code != 200:
        print("Spotify API error:", response.text)
        return {"error": "Spotify API error", "status": response.status_code}
    data = response.json()
    if not data.get("items"):
        return {"error": "No recently played tracks found."}
    last_track_info = data["items"][0]["track"]
    track = {
        "song_name": last_track_info["name"],
        "artist": ", ".join([artist["name"] for artist in last_track_info["artists"]]),
        "album_name": last_track_info["album"]["name"],
        "album_art": last_track_info["album"]["images"][0]["url"],
        "played_at": data["items"][0]["played_at"],
    }
    return track
