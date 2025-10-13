from flask import Blueprint, request, jsonify
import os
import datetime
import requests
from mail import sendEmail
from tools import getClientIP, getGitCommit, json_response
from blueprints.sol import sol_bp


api_bp = Blueprint('api', __name__)
# Register solana blueprint

api_bp.register_blueprint(sol_bp)

NC_CONFIG = requests.get(
    "https://cloud.woodburn.au/s/4ToXgFe3TnnFcN7/download/website-conf.json"
).json()

if 'time-zone' not in NC_CONFIG:
    NC_CONFIG['time-zone'] = 10


@api_bp.route("/")
@api_bp.route("/help")
def help():
    return jsonify({
        "message": "Welcome to Nathan.Woodburn/ API! This is a personal website. For more information, visit https://nathan.woodburn.au",
        "endpoints": {
            "/time": "Get the current time",
            "/timezone": "Get the current timezone",
            "/message": "Get the message from the config",
            "/ip": "Get your IP address",
            "/project": "Get the current project from git",
            "/version": "Get the current version of the website",
            "/help": "Get this help message"
        },
        "base_url": "/api/v1",
        "version": getGitCommit(),
        "ip": getClientIP(request),
        "status": 200
    })


@api_bp.route("/version")
def version():
    return jsonify({"version": getGitCommit()})


@api_bp.route("/time")
def time():
    timezone_offset = datetime.timedelta(hours=NC_CONFIG["time-zone"])
    timezone = datetime.timezone(offset=timezone_offset)
    time = datetime.datetime.now(tz=timezone)
    return jsonify({
        "timestring": time.strftime("%A, %B %d, %Y %I:%M %p"),
        "timestamp": time.timestamp(),
        "timezone": NC_CONFIG["time-zone"],
        "timeISO": time.isoformat(),
        "ip": getClientIP(request),
        "status": 200
    })


@api_bp.route("/timezone")
def timezone():
    return jsonify({
        "timezone": NC_CONFIG["time-zone"],
        "ip": getClientIP(request),
        "status": 200
    })

@api_bp.route("/message")
def message():
    return jsonify({
        "message": NC_CONFIG["message"],
        "ip": getClientIP(request),
        "status": 200
    })


@api_bp.route("/ip")
def ip():
    return jsonify({
        "ip": getClientIP(request),
        "status": 200
    })


@api_bp.route("/email", methods=["POST"])
def email_post():
    # Verify json
    if not request.is_json:
        return json_response(request, "415 Unsupported Media Type", 415)

    # Check if api key sent
    data = request.json
    if not data:
        return json_response(request, "400 Bad Request", 400)

    if "key" not in data:
        return json_response(request, "400 Bad Request 'key' missing", 400)

    if data["key"] != os.getenv("EMAIL_KEY"):
        return json_response(request, "401 Unauthorized", 401)

    # TODO: Add client info to email
    return sendEmail(data)


@api_bp.route("/project")
def project():
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
        return json_response(request, "500 Internal Server Error", 500)

    return jsonify({
        "repo_name": repo_name,
        "repo_description": repo_description,
        "repo": gitinfo,
        "ip": getClientIP(request),
        "status": 200
    })
