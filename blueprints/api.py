from flask import Blueprint, request, jsonify
import os
import datetime
import requests
import re
from mail import sendEmail
from tools import getClientIP, getGitCommit, json_response, parse_date, get_tools_data
from blueprints.sol import sol_bp
from dateutil import parser as date_parser
from blueprints.spotify import get_spotify_track

# Constants
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_UNSUPPORTED_MEDIA = 415
HTTP_SERVER_ERROR = 500

api_bp = Blueprint('api', __name__)
# Register solana blueprint
api_bp.register_blueprint(sol_bp)

# Load configuration
NC_CONFIG = requests.get(
    "https://cloud.woodburn.au/s/4ToXgFe3TnnFcN7/download/website-conf.json"
).json()

if 'time-zone' not in NC_CONFIG:
    NC_CONFIG['time-zone'] = 10


@api_bp.route("/")
@api_bp.route("/help")
def help():
    """Provide API documentation and help."""
    return jsonify({
        "message": "Welcome to Nathan.Woodburn/ API! This is a personal website. For more information, visit https://nathan.woodburn.au",
        "endpoints": {
            "/time": "Get the current time",
            "/timezone": "Get the current timezone",
            "/message": "Get the message from the config",
            "/ip": "Get your IP address",
            "/project": "Get the current project from git",
            "/version": "Get the current version of the website",
            "/page_date?url=URL&verbose=BOOL": "Get the last modified date of a webpage (verbose is optional, default false)",
            "/tools": "Get a list of tools used by Nathan Woodburn",
            "/playing": "Get the currently playing Spotify track",
            "/status": "Just check if the site is up",
            "/ping": "Just check if the site is up",
            "/help": "Get this help message"
        },
        "base_url": "/api/v1",
        "version": getGitCommit(),
        "ip": getClientIP(request),
        "status": HTTP_OK
    })

@api_bp.route("/status")
@api_bp.route("/ping")
def status():
    return json_response(request, "200 OK", HTTP_OK)

@api_bp.route("/version")
def version():
    """Get the current version of the website."""
    return jsonify({"version": getGitCommit()})


@api_bp.route("/time")
def time():
    """Get the current time in the configured timezone."""
    timezone_offset = datetime.timedelta(hours=NC_CONFIG["time-zone"])
    timezone = datetime.timezone(offset=timezone_offset)
    current_time = datetime.datetime.now(tz=timezone)
    return jsonify({
        "timestring": current_time.strftime("%A, %B %d, %Y %I:%M %p"),
        "timestamp": current_time.timestamp(),
        "timezone": NC_CONFIG["time-zone"],
        "timeISO": current_time.isoformat(),
        "ip": getClientIP(request),
        "status": HTTP_OK
    })


@api_bp.route("/timezone")
def timezone():
    """Get the current timezone setting."""
    return jsonify({
        "timezone": NC_CONFIG["time-zone"],
        "ip": getClientIP(request),
        "status": HTTP_OK
    })


@api_bp.route("/message")
def message():
    """Get the message from the configuration."""
    return jsonify({
        "message": NC_CONFIG["message"],
        "ip": getClientIP(request),
        "status": HTTP_OK
    })


@api_bp.route("/ip")
def ip():
    """Get the client's IP address."""
    return jsonify({
        "ip": getClientIP(request),
        "status": HTTP_OK
    })


@api_bp.route("/email", methods=["POST"])
def email_post():
    """Send an email via the API (requires API key)."""
    # Verify json
    if not request.is_json:
        return json_response(request, "415 Unsupported Media Type", HTTP_UNSUPPORTED_MEDIA)

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


@api_bp.route("/project")
def project():
    """Get information about the current git project."""
    gitinfo = {
        "website": None,
    }
    try:
        git = requests.get(
            "https://git.woodburn.au/api/v1/users/nathanwoodburn/activities/feeds?only-performed-by=true&limit=1",
            headers={"Authorization": os.getenv("git_token")},
        )
        git = git.json()        
        git = git[0]
        repo_name = git["repo"]["name"]
        repo_name = repo_name.lower()
        repo_description = git["repo"]["description"]
        gitinfo["name"] = repo_name
        gitinfo["description"] = repo_description
        gitinfo["url"] = git["repo"]["html_url"]
        if "website" in git["repo"]:
            gitinfo["website"] = git["repo"]["website"]
    except Exception as e:
        print(f"Error getting git data: {e}")
        return json_response(request, "500 Internal Server Error", HTTP_SERVER_ERROR)

    return jsonify({
        "repo_name": repo_name,
        "repo_description": repo_description,
        "repo": gitinfo,
        "ip": getClientIP(request),
        "status": HTTP_OK
    })

@api_bp.route("/tools")
def tools():
    """Get a list of tools used by Nathan Woodburn."""
    try:
        tools = get_tools_data()
    except Exception as e:
        print(f"Error getting tools data: {e}")
        return json_response(request, "500 Internal Server Error", HTTP_SERVER_ERROR)

    # Remove demo and move demo_url to demo
    for tool in tools:
        if "demo_url" in tool:
            tool["demo"] = tool.pop("demo_url")
        
    return json_response(request, {"tools": tools}, HTTP_OK)

@api_bp.route("/playing")
def playing():
    """Get the currently playing Spotify track."""
    track_info = get_spotify_track()
    if "error" in track_info:
        return json_response(request, track_info, HTTP_OK)
    return json_response(request, {"spotify": track_info}, HTTP_OK)

@api_bp.route("/page_date")
def page_date():
    url = request.args.get("url")
    if not url:
        return json_response(request, "400 Bad Request 'url' missing", HTTP_BAD_REQUEST)

    verbose = request.args.get("verbose", "").lower() in ["true", "1", "yes", "y"]

    if not url.startswith(("https://", "http://")):
        return json_response(request, "400 Bad Request 'url' invalid", HTTP_BAD_REQUEST)

    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        return json_response(request, f"400 Bad Request 'url' unreachable: {e}", HTTP_BAD_REQUEST)

    page_text = r.text

    # Remove ordinal suffixes globally
    page_text = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', page_text, flags=re.IGNORECASE)
    # Remove HTML comments
    page_text = re.sub(r'<!--.*?-->', '', page_text, flags=re.DOTALL)

    date_patterns = [
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',                             # YYYY-MM-DD
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',                             # DD-MM-YYYY
        r'(?:Last updated:|Updated:|Updated last:)?\s*(\d{1,2})\s+([A-Za-z]{3,9})[, ]?\s*(\d{4})',  # DD Month YYYY
        r'(?:\b\w+\b\s+){0,3}([A-Za-z]{3,9})\s+(\d{1,2}),?\s*(\d{4})',    # Month DD, YYYY with optional words
        r'\b(\d{4})(\d{2})(\d{2})\b',                                     # YYYYMMDD
        r'(?:Last updated:|Updated:|Last update)?\s*([A-Za-z]{3,9})\s+(\d{4})',  # Month YYYY only
    ]



    # Structured data patterns
    json_date_patterns = {
        r'"datePublished"\s*:\s*"([^"]+)"': "published",
        r'"dateModified"\s*:\s*"([^"]+)"': "modified",
        r'<meta\s+(?:[^>]*?)property\s*=\s*"article:published_time"\s+content\s*=\s*"([^"]+)"': "published",
        r'<meta\s+(?:[^>]*?)property\s*=\s*"article:modified_time"\s+content\s*=\s*"([^"]+)"': "modified",
        r'<time\s+datetime\s*=\s*"([^"]+)"': "published"
    }

    found_dates = []

    # Extract content dates
    for idx, pattern in enumerate(date_patterns):
        for match in re.findall(pattern, page_text):
            if not match:
                continue
            groups = match[-3:]  # last three elements
            found_dates.append([groups, idx, "content"])

    # Extract structured data dates
    for pattern, date_type in json_date_patterns.items():
        for match in re.findall(pattern, page_text):
            try:
                dt = date_parser.isoparse(match)
                formatted_date = dt.strftime('%Y-%m-%d')
                found_dates.append([[formatted_date], -1, date_type])
            except (ValueError, TypeError):
                continue

    if not found_dates:
        return json_response(request, "Date not found on page", HTTP_BAD_REQUEST)

    today = datetime.date.today()
    tolerance_date = today + datetime.timedelta(days=1) # Allow for slight future dates (e.g., time zones)
    # When processing dates
    processed_dates = []
    for date_groups, pattern_format, date_type in found_dates:
        if pattern_format == -1:
            # Already formatted date
            try:
                dt = datetime.datetime.strptime(date_groups[0], "%Y-%m-%d").date()
            except ValueError:
                continue
        else:
            parsed_date = parse_date(date_groups)
            if not parsed_date:
                continue
            dt = datetime.datetime.strptime(parsed_date, "%Y-%m-%d").date()

        # Only keep dates in the past (with tolerance)
        if dt <= tolerance_date:
            date_obj = {"date": dt.strftime("%Y-%m-%d"), "type": date_type}
            if verbose:
                if pattern_format == -1:
                    date_obj.update({"source": "metadata", "pattern_used": pattern_format, "raw": date_groups[0]})
                else:
                    date_obj.update({"source": "content", "pattern_used": pattern_format, "raw": " ".join(date_groups)})
            processed_dates.append(date_obj)

    if not processed_dates:
        if verbose:
            return jsonify({
                "message": "No valid dates found on page",
                "found_dates": found_dates,
                "processed_dates": processed_dates
            }), HTTP_BAD_REQUEST
        return json_response(request, "No valid dates found on page", HTTP_BAD_REQUEST)
    # Sort dates and return latest
    processed_dates.sort(key=lambda x: x["date"])
    latest = processed_dates[-1]

    response = {"latest": latest["date"], "type": latest["type"]}
    if verbose:
        response["dates"] = processed_dates

    return json_response(request, response, HTTP_OK)
