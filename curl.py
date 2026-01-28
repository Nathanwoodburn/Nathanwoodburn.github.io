from flask import render_template
from tools import getAddress, get_tools_data, getClientIP
import os
from functools import lru_cache
from blueprints.spotify import get_playing_spotify_track
from cache_helper import get_git_latest_activity, get_projects as get_projects_cached


MAX_WIDTH = 80


def clean_path(path: str):
    path = path.strip("/ ").lower()
    # Strip any .html extension
    if path.endswith(".html"):
        path = path[:-5]

    # If the path is empty, set it to "index"
    if path == "":
        path = "index"
    return path


@lru_cache(maxsize=1)
def get_header():
    with open("templates/header.ascii", "r") as f:
        return f.read()


@lru_cache(maxsize=16)
def get_current_project():
    git = get_git_latest_activity()
    repo_name = git["repo"]["name"].lower()
    repo_description = git["repo"]["description"]
    if not repo_description:
        return f"[1;36m{repo_name}[0m"
    return f"[1;36m{repo_name}[0m - [1m{repo_description}[0m"


@lru_cache(maxsize=16)
def get_projects():
    projects_data = get_projects_cached(limit=5)
    projects = ""
    for project in projects_data:
        projects += f"""[1m{project["name"]}[0m - {project["description"] if project["description"] else "No description"}
{project["html_url"]}

"""
    return projects


def curl_response(request):
    # Check if <path>.ascii exists
    path = clean_path(request.path)

    # Handle special cases
    if path == "index":
        # Get current project
        return (
            render_template(
                "index.ascii",
                repo=get_current_project(),
                ip=getClientIP(request),
                spotify=get_playing_spotify_track(),
            ),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
    if path == "projects":
        # Get projects
        return (
            render_template(
                "projects.ascii", header=get_header(), projects=get_projects()
            ),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    if path == "donate":
        # Get donation info
        return (
            render_template(
                "donate.ascii",
                header=get_header(),
                HNS=getAddress("HNS"),
                BTC=getAddress("BTC"),
                SOL=getAddress("SOL"),
                ETH=getAddress("ETH"),
            ),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    if path == "donate/more":
        coinList = os.listdir(".well-known/wallets")
        coinList = [file for file in coinList if file[0] != "."]
        coinList.sort()
        return (
            render_template("donate_more.ascii", header=get_header(), coins=coinList),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    # For other donation pages, fall back to ascii if it exists
    if path.startswith("donate/"):
        coin = path.split("/")[1]
        address = getAddress(coin)
        if address != "":
            return (
                render_template(
                    "donate_coin.ascii",
                    header=get_header(),
                    coin=coin.upper(),
                    address=address,
                ),
                200,
                {"Content-Type": "text/plain; charset=utf-8"},
            )

    if path == "tools":
        tools = get_tools_data()
        return (
            render_template("tools.ascii", header=get_header(), tools=tools),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    if os.path.exists(f"templates/{path}.ascii"):
        return (
            render_template(f"{path}.ascii", header=get_header()),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    # Fallback to html if it exists
    if os.path.exists(f"templates/{path}.html"):
        return render_template(f"{path}.html")

    # Return curl error page
    error = {
        "code": 404,
        "message": "The requested resource was not found on this server.",
    }
    return (
        render_template("error.ascii", header=get_header(), error=error),
        404,
        {"Content-Type": "text/plain; charset=utf-8"},
    )
