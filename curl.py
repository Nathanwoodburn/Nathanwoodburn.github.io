from flask import render_template
from tools import error_response, getAddress
import os
from functools import lru_cache
import requests


def clean_path(path:str):
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

@lru_cache(maxsize=1)
def get_current_project():
    git = requests.get(
        "https://git.woodburn.au/api/v1/users/nathanwoodburn/activities/feeds?only-performed-by=true&limit=1",
        headers={"Authorization": os.getenv("GIT_AUTH") if os.getenv("GIT_AUTH") else os.getenv("git_token")},
    )
    git = git.json()
    git = git[0]
    repo_name = git["repo"]["name"]
    repo_name = repo_name.lower()
    repo_description = git["repo"]["description"]    
    return f"[1m{repo_name}[0m - {repo_description}"


@lru_cache(maxsize=1)
def get_projects():
    projectsreq = requests.get(
            "https://git.woodburn.au/api/v1/users/nathanwoodburn/repos"
        )

    projects = projectsreq.json()

    # Check for next page
    pageNum = 1
    while 'rel="next"' in projectsreq.headers["link"]:
        projectsreq = requests.get(
            "https://git.woodburn.au/api/v1/users/nathanwoodburn/repos?page="
            + str(pageNum)
        )
        projects += projectsreq.json()
        pageNum += 1

    # Sort by last updated
    projectsList = sorted(
        projects, key=lambda x: x["updated_at"], reverse=True)
    projects = ""
    projectNum = 0
    includedNames = []
    while len(includedNames) < 5 and projectNum < len(projectsList):
        # Avoid duplicates
        if projectsList[projectNum]["name"] in includedNames:
            projectNum += 1
            continue
        includedNames.append(projectsList[projectNum]["name"])
        project = projectsList[projectNum]
        projects += f"""[1m{project['name']}[0m - {project['description'] if project['description'] else 'No description'}
{project['html_url']}

"""
        projectNum += 1
        
    return projects

def curl_response(request):
    # Check if <path>.ascii exists
    path = clean_path(request.path)
    
    # Handle special cases
    if path == "index":
        # Get current project
        return render_template("index.ascii",header=get_header(),repo=get_current_project()), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    if path == "projects":
        # Get projects
        return render_template("projects.ascii",header=get_header(),projects=get_projects()), 200, {'Content-Type': 'text/plain; charset=utf-8'}

    if path == "donate":
        # Get donation info
        return render_template("donate.ascii",header=get_header(),
                               HNS=getAddress("HNS"), BTC=getAddress("BTC"),
                               SOL=getAddress("SOL"), ETH=getAddress("ETH")
                               ), 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    if path == "donate/more":
        coinList = os.listdir(".well-known/wallets")
        coinList = [file for file in coinList if file[0] != "."]
        coinList.sort()
        return render_template("donate_more.ascii",header=get_header(),
                               coins=coinList
                               ), 200, {'Content-Type': 'text/plain; charset=utf-8'}

        
                               
    # For other donation pages, fall back to ascii if it exists
    if path.startswith("donate/"):
        coin = path.split("/")[1]
        address = getAddress(coin)
        if address != "":
            return render_template("donate_coin.ascii",header=get_header(),coin=coin.upper(),address=address), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    

    if os.path.exists(f"templates/{path}.ascii"):
        return render_template(f"{path}.ascii",header=get_header()), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    # Fallback to html if it exists
    if os.path.exists(f"templates/{path}.html"):
        return render_template(f"{path}.html")
    
    return error_response(request)