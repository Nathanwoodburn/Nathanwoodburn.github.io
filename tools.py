from flask import Request, render_template, jsonify
import os
from functools import cache

def getClientIP(request):
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.remote_addr
    return ip

def isCurl(request: Request) -> bool:
    """
    Check if the request is from curl
    
    Args:
        request (Request): The Flask request object
    Returns:
        bool: True if the request is from curl, False otherwise

    """
    if request.headers and request.headers.get("User-Agent"):
        # Check if curl
        if "curl" in request.headers.get("User-Agent", "curl"):
            return True
    return False

def isCrawler(request: Request) -> bool:
    """
    Check if the request is from a web crawler (e.g., Googlebot, Bingbot)
    Args:
        request (Request): The Flask request object
    Returns:
        bool: True if the request is from a web crawler, False otherwise
    """

    if request.headers and request.headers.get("User-Agent"):
        # Check if Googlebot or Bingbot
        if "Googlebot" in request.headers.get(
            "User-Agent", ""
        ) or "Bingbot" in request.headers.get("User-Agent", ""):
            return True
    return False


@cache
def getAddress(coin: str) -> str:
    address = ""
    if os.path.isfile(".well-known/wallets/" + coin.upper()):
        with open(".well-known/wallets/" + coin.upper()) as file:
            address = file.read()
    return address


def getFilePath(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)

def error_response(request: Request, message: str = "404 Not Found", code: int = 404):
    if isCurl(request):
        return jsonify(
            {
                "status": code,
                "message": message,
                "ip": getClientIP(request),
            }
        ), code
    
    # Check if <error code>.html exists in templates
    if os.path.isfile(f"templates/{code}.html"):
        return render_template(f"{code}.html"), code
    return render_template("404.html"), code