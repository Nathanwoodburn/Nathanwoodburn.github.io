import datetime
import os
from zoneinfo import ZoneInfo

import dotenv
from flask import Blueprint, jsonify, request

dotenv.load_dotenv()

from blueprints import sol
from blueprints.spotify import get_playing_spotify_track
from cache_helper import get_git_latest_activity
from mail import sendEmail
from tools import get_tools_data, getClientIP, getGitCommit, json_response

# Constants
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_UNSUPPORTED_MEDIA = 415
HTTP_SERVER_ERROR = 500

app = Blueprint("api", __name__, url_prefix="/api/v1")
# Register solana blueprint
app.register_blueprint(sol.app)

tz = ZoneInfo(os.getenv("TIMEZONE", "Australia/Sydney"))


@app.route("/", strict_slashes=False)
@app.route("/help")
def help():
    """Provide API documentation and help."""
    return jsonify(
        {
            "message": "Welcome to Nathan.Woodburn/ API! This is a personal website. For more information, visit https://nathan.woodburn.au",
            "endpoints": {
                "/time": "Get the current time",
                "/timezone": "Get the current timezone",
                "/project": "Get the current project from git",
                "/version": "Get the current version of the website",
                "/tools": "Get a list of tools used by Nathan Woodburn",
                "/playing": "Get the currently playing Spotify track",
                "/status": "Just check if the site is up",
                "/ping": "Just check if the site is up",
                "/ip": "Get your IP address",
                "/headers": "Get your request headers",
                "/help": "Get this help message",
            },
            "base_url": "/api/v1",
            "version": getGitCommit(),
            "ip": getClientIP(request),
            "status": HTTP_OK,
        }
    )


@app.route("/status")
@app.route("/ping")
def status():
    return json_response(request, "200 OK", HTTP_OK)


@app.route("/version")
def version():
    """Get the current version of the website."""
    return jsonify({"version": getGitCommit()})


@app.route("/time")
def time():
    """Get the current time in the configured timezone."""

    current_time = datetime.datetime.now(tz)
    return jsonify(
        {
            "timestring": current_time.strftime("%A, %B %d, %Y %I:%M %p"),
            "timestamp": current_time.timestamp(),
            "timezone": tz.tzname(current_time),
            "timeISO": current_time.isoformat(),
            "ip": getClientIP(request),
            "status": HTTP_OK,
        }
    )


@app.route("/timezone")
def timezone():
    """Get the current timezone setting."""
    current_time = datetime.datetime.now(tz)
    return jsonify(
        {
            "timezone": tz.utcoffset(current_time).total_seconds() / 3600,  # type: ignore
            "timezone_name": tz.tzname(current_time),
            "ip": getClientIP(request),
            "status": HTTP_OK,
        }
    )


@app.route("/message")
def message():
    """Deprecated: Get the message from the config."""
    return jsonify(
        {
            "message": "",
            "ip": getClientIP(request),
            "status": HTTP_OK,
            "deprecated": True,
            "note": "The /message endpoint is deprecated and will be removed in a future version. It currently returns an empty message.",
        }
    )


@app.route("/ip")
def ip():
    """Get the client's IP address."""
    return jsonify({"ip": getClientIP(request), "status": HTTP_OK})


@app.route("/email", methods=["POST"])
def email_post():
    """Send an email via the API (requires API key)."""
    # Verify json
    if not request.is_json:
        return json_response(
            request, "415 Unsupported Media Type", HTTP_UNSUPPORTED_MEDIA
        )

    # Check if api key sent
    data = request.json
    if not data:
        return json_response(request, "400 Bad Request", HTTP_BAD_REQUEST)

    if "key" not in data:
        return json_response(request, "400 Bad Request 'key' missing", HTTP_BAD_REQUEST)

    if data["key"] != os.getenv("EMAIL_KEY"):
        return json_response(request, "401 Unauthorized", HTTP_UNAUTHORIZED)

    # TODO: Add client info to email
    return sendEmail(data)


@app.route("/project")
def project():
    """Get information about the current git project."""
    git = get_git_latest_activity()
    repo_name = git["repo"]["name"].lower()
    repo_description = git["repo"]["description"]

    gitinfo = {
        "name": repo_name,
        "description": repo_description,
        "url": git["repo"]["html_url"],
        "website": git["repo"].get("website"),
    }

    return jsonify(
        {
            "repo_name": repo_name,
            "repo_description": repo_description,
            "repo": gitinfo,
            "ip": getClientIP(request),
            "status": HTTP_OK,
        }
    )


@app.route("/tools")
def tools():
    """Get a list of tools used by Nathan Woodburn."""
    return json_response(request, {"tools": get_tools_data()}, HTTP_OK)


@app.route("/playing")
def playing():
    """Get the currently playing Spotify track."""
    track_info = get_playing_spotify_track()
    if "error" in track_info:
        return json_response(request, track_info, HTTP_OK)
    return json_response(request, {"spotify": track_info}, HTTP_OK)


@app.route("/headers")
def headers():
    """Get the request headers."""
    headers = dict(request.headers)

    # For each header, convert list-like headers to lists
    toremove = []
    for key in headers:
        # If header is like X- something
        if key.startswith("X-"):
            # Remove from headers
            toremove.append(key)

    for key in toremove:
        headers.pop(key)

    return jsonify({"headers": headers, "ip": getClientIP(request), "status": HTTP_OK})
