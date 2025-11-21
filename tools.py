from flask import Request, render_template, jsonify, make_response
import os
from functools import lru_cache
import datetime
from typing import Optional, Dict, Union, Tuple
import re
from dateutil.parser import parse
import json

# HTTP status codes
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404

CRAWLERS = [
    "Googlebot",
    "Bingbot",
    "Chrome-Lighthouse",
    "Slurp",
    "DuckDuckBot",
    "Baiduspider",
    "YandexBot",
    "Sogou",
    "Exabot",
    "facebot",
    "ia_archiver",
    "Twitterbot",
]

CLI_AGENTS = ["curl", "hurl", "xh", "Posting", "HTTPie", "nushell"]


def getClientIP(request: Request) -> str:
    """
    Get the client's IP address from the request.

    Args:
        request (Request): The Flask request object

    Returns:
        str: The client's IP address
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.remote_addr
    if ip is None:
        ip = "unknown"
    return ip


@lru_cache(maxsize=1)
def getGitCommit() -> str:
    """
    Get the current git commit hash.

    Returns:
        str: The current git commit hash or a failure message
    """
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


def isCLI(request: Request) -> bool:
    """
    Check if the request is from curl or hurl.

    Args:
        request (Request): The Flask request object

    Returns:
        bool: True if the request is from curl or hurl, False otherwise
    """
    if request.headers and request.headers.get("User-Agent"):
        user_agent = request.headers.get("User-Agent", "")
        return any(agent in user_agent for agent in CLI_AGENTS)
    return False


def isCrawler(request: Request) -> bool:
    """
    Check if the request is from a web crawler (e.g., Googlebot, Bingbot).

    Args:
        request (Request): The Flask request object

    Returns:
        bool: True if the request is from a web crawler, False otherwise
    """
    if request.headers and request.headers.get("User-Agent"):
        user_agent = request.headers.get("User-Agent", "")
        return any(crawler in user_agent for crawler in CRAWLERS)
    return False


@lru_cache(maxsize=128)
def isDev(host: str) -> bool:
    """
    Check if the host indicates a development environment.

    Args:
        host (str): The host string from the request

    Returns:
        bool: True if in development environment, False otherwise
    """
    if (
        host == "localhost:5000"
        or host == "127.0.0.1:5000"
        or os.getenv("DEV") == "true"
        or host == "test.nathan.woodburn.au"
    ):
        return True
    return False


@lru_cache(maxsize=128)
def getHandshakeScript(host: str) -> str:
    """
    Get the handshake script HTML snippet.

    Args:
        domain (str): The domain to use in the handshake script

    Returns:
        str: The handshake script HTML snippet
    """
    if isDev(host):
        return ""
    return '<script src="https://nathan.woodburn/handshake.js" domain="nathan.woodburn" async></script><script src="https://nathan.woodburn/https.js" async></script>'


@lru_cache(maxsize=64)
def getAddress(coin: str) -> str:
    """
    Get the wallet address for a cryptocurrency.

    Args:
        coin (str): The cryptocurrency code

    Returns:
        str: The wallet address or empty string if not found
    """
    address = ""
    wallet_path = f".well-known/wallets/{coin.upper()}"
    if os.path.isfile(wallet_path):
        with open(wallet_path) as file:
            address = file.read()
    return address


@lru_cache(maxsize=256)
def getFilePath(name: str, path: str) -> Optional[str]:
    """
    Find a file in a directory tree.

    Args:
        name (str): The filename to find
        path (str): The root directory to search

    Returns:
        Optional[str]: The full path to the file or None if not found
    """
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None


def json_response(
    request: Request, message: Union[str, Dict] = "404 Not Found", code: int = 404
):
    """
    Create a JSON response with standard formatting.

    Args:
        request (Request): The Flask request object
        message (Union[str, Dict]): The response message or data
        code (int): The HTTP status code

    Returns:
        Tuple[Dict, int]: The JSON response and HTTP status code
    """
    if isinstance(message, dict):
        # Add status and ip to dict
        message["status"] = code
        message["ip"] = getClientIP(request)
        return jsonify(message), code

    return jsonify(
        {
            "status": code,
            "message": message,
            "ip": getClientIP(request),
        }
    ), code


def error_response(
    request: Request,
    message: str = "404 Not Found",
    code: int = 404,
    force_json: bool = False,
) -> Union[Tuple[Dict, int], object]:
    """
    Create an error response in JSON or HTML format.

    Args:
        request (Request): The Flask request object
        message (str): The error message
        code (int): The HTTP status code
        force_json (bool): Whether to force JSON response regardless of client

    Returns:
        Union[Tuple[Dict, int], object]: The JSON or HTML response
    """
    if force_json or isCLI(request):
        return json_response(request, message, code)

    # Check if <error code>.html exists in templates
    template_name = (
        f"{code}.html" if os.path.isfile(f"templates/{code}.html") else "404.html"
    )
    response = make_response(
        render_template(template_name, code=code, message=message), code
    )

    # Add message to response headers
    response.headers["X-Error-Message"] = message
    return response


def parse_date(date_groups: list[str]) -> str | None:
    """
    Parse a list of date components into YYYY-MM-DD format.
    Uses dateutil.parser for robust parsing.
    Works for:
      - DD Month YYYY
      - Month DD, YYYY
      - YYYY-MM-DD
      - YYYYMMDD
      - Month YYYY (defaults day to 1)
      - Handles ordinal suffixes (st, nd, rd, th)
    """
    try:
        # Join date groups into a single string
        date_str = " ".join(date_groups).strip()

        # Remove ordinal suffixes
        date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str, flags=re.IGNORECASE)

        # Parse with dateutil, default day=1 if missing
        dt = parse(date_str, default=datetime.datetime(1900, 1, 1))

        # If year is missing, parse will fallback to 1900 → reject
        if dt.year == 1900:
            return None

        return dt.strftime("%Y-%m-%d")

    except (ValueError, TypeError):
        return None


def get_tools_data():
    with open("data/tools.json", "r") as f:
        return json.load(f)
