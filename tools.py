from flask import Request
import os
from functools import cache

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