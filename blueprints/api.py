from flask import Blueprint, request, jsonify, make_response
import os
import datetime
import requests
from mail import sendEmail
from sol import create_transaction


api_bp = Blueprint('api', __name__)

ncReq = requests.get(
    "https://cloud.woodburn.au/s/4ToXgFe3TnnFcN7/download/website-conf.json"
)
ncConfig = ncReq.json()

if 'time-zone' not in ncConfig:
    ncConfig['time-zone'] = 10


def getClientIP(request):
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.remote_addr
    return ip

def getGitCommit():
    # if .git exists, get the latest commit hash
    if os.path.isdir(".git"):
        git_dir = ".git"
        head_ref = ""
        with open(os.path.join(git_dir, "HEAD")) as file:
            head_ref = file.read().strip()
        if head_ref.startswith("ref: "):
            head_ref = head_ref[5:]
            with open(os.path.join(git_dir, head_ref)) as file:
                return file.read().strip()
        else:
            return head_ref

    # Check if env SOURCE_COMMIT is set
    if "SOURCE_COMMIT" in os.environ:
        return os.environ["SOURCE_COMMIT"]

    return "failed to get version"

@api_bp.route("/")
@api_bp.route("/help")
def help_get():
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
        "version": getGitCommit()
    })

@api_bp.route("/version")
def version_get():
    return jsonify({"version": getGitCommit()})

@api_bp.route("/time")
def time_get():
    timezone_offset = datetime.timedelta(hours=ncConfig["time-zone"])
    timezone = datetime.timezone(offset=timezone_offset)
    time = datetime.datetime.now(tz=timezone)
    return jsonify({
        "timestring": time.strftime("%A, %B %d, %Y %I:%M %p"),
        "timestamp": time.timestamp(),
        "timezone": ncConfig["time-zone"],
        "timeISO": time.isoformat()
    })

@api_bp.route("/timezone")
def timezone_get():
    return jsonify({"timezone": ncConfig["time-zone"]})

@api_bp.route("/timezone", methods=["POST"])
def timezone_post():
    # Refresh config
    global ncConfig
    conf = requests.get(
        "https://cloud.woodburn.au/s/4ToXgFe3TnnFcN7/download/website-conf.json")
    if conf.status_code != 200:
        return jsonify({"message": "Error: Could not get timezone"})
    if not conf.json():
        return jsonify({"message": "Error: Could not get timezone"})
    conf = conf.json()
    if "time-zone" not in conf:
        return jsonify({"message": "Error: Could not get timezone"})

    ncConfig = conf
    return jsonify({"message": "Successfully pulled latest timezone", "timezone": ncConfig["time-zone"]})

@api_bp.route("/message")
def message_get():
    return jsonify({"message": ncConfig["message"]})


@api_bp.route("/ip")
def ip_get():
    return jsonify({"ip": getClientIP(request)})


@api_bp.route("/email", methods=["POST"])
def email_post():
    # Verify json
    if not request.is_json:
        return jsonify({
            "status": 400,
            "error": "Bad request JSON Data missing"
        })

    # Check if api key sent
    data = request.json
    if not data:
        return jsonify({
            "status": 400,
            "error": "Bad request JSON Data missing"
        })

    if "key" not in data:
        return jsonify({
            "status": 401,
            "error": "Unauthorized 'key' missing"
        })

    if data["key"] != os.getenv("EMAIL_KEY"):
        return jsonify({
            "status": 401,
            "error": "Unauthorized 'key' invalid"
        })

    return sendEmail(data)


@api_bp.route("/project")
def project_get():
    try:
        git = requests.get(
            "https://git.woodburn.au/users/nathanwoodburn/activities/feeds?only-performed-by=true&limit=1",
            headers={"Authorization": os.getenv("git_token")},
        )
        git = git.json()
        git = git[0]
        repo_name = git["repo"]["name"]
        repo_name = repo_name.lower()
        repo_description = git["repo"]["description"]
    except Exception as e:
        repo_name = "nathanwoodburn.github.io"
        repo_description = "Personal website"
        git = {
            "repo": {
                "html_url": "https://nathan.woodburn.au",
                "name": "nathanwoodburn.github.io",
                "description": "Personal website",
            }
        }
        print(f"Error getting git data: {e}")

    return jsonify({
        "repo_name": repo_name,
        "repo_description": repo_description,
        "git": git,
    })

# region Solana Links
SOLANA_HEADERS = {
    "Content-Type": "application/json",
    "X-Action-Version": "2.4.2",
    "X-Blockchain-Ids": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
}



@api_bp.route("/donate", methods=["GET", "OPTIONS"])
def sol_donate_get():
    data = {
        "icon": "https://nathan.woodburn.au/assets/img/profile.png",
        "label": "Donate to Nathan.Woodburn/",
        "title": "Donate to Nathan.Woodburn/",
        "description": "Student, developer, and crypto enthusiast",
        "links": {
            "actions": [
                {"label": "0.01 SOL", "href": "/api/v1/donate/0.01"},
                {"label": "0.1 SOL", "href": "/api/v1/donate/0.1"},
                {"label": "1 SOL", "href": "/api/v1/donate/1"},
                {
                    "href": "/api/v1/donate/{amount}",
                    "label": "Donate",
                    "parameters": [
                        {"name": "amount", "label": "Enter a custom SOL amount"}
                    ],
                },
            ]
        },
    }

    response = make_response(jsonify(data), 200, SOLANA_HEADERS)

    if request.method == "OPTIONS":
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type,Authorization,Content-Encoding,Accept-Encoding,X-Action-Version,X-Blockchain-Ids"
        )

    return response


@api_bp.route("/donate/<amount>")
def sol_donate_amount_get(amount):
    data = {
        "icon": "https://nathan.woodburn.au/assets/img/profile.png",
        "label": f"Donate {amount} SOL to Nathan.Woodburn/",
        "title": "Donate to Nathan.Woodburn/",
        "description": f"Donate {amount} SOL to Nathan.Woodburn/",
    }
    return jsonify(data), 200, SOLANA_HEADERS


@api_bp.route("/donate/<amount>", methods=["POST"])
def sol_donate_post(amount):

    if not request.json:
        return jsonify({"message": "Error: No JSON data provided"}), 400, SOLANA_HEADERS
    
    
    if "account" not in request.json:
        return jsonify({"message": "Error: No account provided"}), 400, SOLANA_HEADERS

    sender = request.json["account"]

    # Make sure amount is a number
    try:
        amount = float(amount)
    except ValueError:
        amount = 1 # Default to 1 SOL if invalid

    if amount < 0.0001:
        return jsonify({"message": "Error: Amount too small"}), 400, SOLANA_HEADERS

    transaction = create_transaction(sender, amount)
    return jsonify({"message": "Success", "transaction": transaction}), 200, SOLANA_HEADERS

# endregion

