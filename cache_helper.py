"""
Cache helper module for expensive API calls and configuration.
Provides centralized caching with TTL for external API calls.
"""

import datetime
import os
import json
import requests
from functools import lru_cache


# Cache storage for NC_CONFIG with timestamp
_nc_config_cache = {"data": None, "timestamp": 0}
_nc_config_ttl = 3600  # 1 hour cache


def get_nc_config():
    """
    Get NC_CONFIG with caching (1 hour TTL).
    Falls back to default config on error.

    Returns:
        dict: Configuration dictionary
    """
    global _nc_config_cache
    current_time = datetime.datetime.now().timestamp()

    # Check if cache is valid
    if (
        _nc_config_cache["data"]
        and (current_time - _nc_config_cache["timestamp"]) < _nc_config_ttl
    ):
        return _nc_config_cache["data"]

    # Fetch new config
    try:
        config = requests.get(
            "https://cloud.woodburn.au/s/4ToXgFe3TnnFcN7/download/website-conf.json",
            timeout=5,
        ).json()
        _nc_config_cache = {"data": config, "timestamp": current_time}
        return config
    except Exception as e:
        print(f"Error fetching NC_CONFIG: {e}")
        # Return cached data if available, otherwise default
        if _nc_config_cache["data"]:
            return _nc_config_cache["data"]
        return {"time-zone": 10, "message": ""}


# Cache storage for git data
_git_data_cache = {"data": None, "timestamp": 0}
_git_data_ttl = 300  # 5 minutes cache


def get_git_latest_activity():
    """
    Get latest git activity with caching (5 minute TTL).

    Returns:
        dict: Git activity data or default values
    """
    global _git_data_cache
    current_time = datetime.datetime.now().timestamp()

    # Check if cache is valid
    if (
        _git_data_cache["data"]
        and (current_time - _git_data_cache["timestamp"]) < _git_data_ttl
    ):
        return _git_data_cache["data"]

    # Fetch new data
    try:
        git = requests.get(
            "https://git.woodburn.au/api/v1/users/nathanwoodburn/activities/feeds?only-performed-by=true&limit=1",
            headers={
                "Authorization": os.getenv("GIT_AUTH") or os.getenv("git_token") or ""
            },
            timeout=5,
        )
        git_data = git.json()
        if git_data and len(git_data) > 0:
            result = git_data[0]
            _git_data_cache = {"data": result, "timestamp": current_time}
            return result
    except Exception as e:
        print(f"Error fetching git data: {e}")

    # Return cached or default
    if _git_data_cache["data"]:
        return _git_data_cache["data"]

    return {
        "repo": {
            "html_url": "https://nathan.woodburn.au",
            "name": "nathanwoodburn.github.io",
            "description": "Personal website",
        }
    }


# Cache storage for projects
_projects_cache = {"data": None, "timestamp": 0}
_projects_ttl = 7200  # 2 hours cache


def get_projects(limit=3):
    """
    Get projects list with caching (2 hour TTL).

    Args:
        limit (int): Number of projects to return

    Returns:
        list: List of project dictionaries
    """
    global _projects_cache
    current_time = datetime.datetime.now().timestamp()

    # Check if cache is valid
    if (
        _projects_cache["data"]
        and (current_time - _projects_cache["timestamp"]) < _projects_ttl
    ):
        return _projects_cache["data"][:limit]

    # Fetch new data
    try:
        projects = []
        projectsreq = requests.get(
            "https://git.woodburn.au/api/v1/users/nathanwoodburn/repos", timeout=5
        )
        projects = projectsreq.json()

        # Check for pagination
        pageNum = 2
        while 'rel="next"' in projectsreq.headers.get("link", ""):
            projectsreq = requests.get(
                f"https://git.woodburn.au/api/v1/users/nathanwoodburn/repos?page={pageNum}",
                timeout=5,
            )
            projects += projectsreq.json()
            pageNum += 1
            # Safety limit
            if pageNum > 10:
                break

        # Process projects
        for project in projects:
            if project.get("avatar_url") in ("https://git.woodburn.au/", ""):
                project["avatar_url"] = "/favicon.png"
            project["name"] = project["name"].replace("_", " ").replace("-", " ")

        # Sort by last updated
        projects_sorted = sorted(
            projects, key=lambda x: x.get("updated_at", ""), reverse=True
        )

        # Remove duplicates by name
        seen_names = set()
        unique_projects = []
        for project in projects_sorted:
            if project["name"] not in seen_names:
                unique_projects.append(project)
                seen_names.add(project["name"])

        _projects_cache = {"data": unique_projects, "timestamp": current_time}
        return unique_projects[:limit]
    except Exception as e:
        print(f"Error fetching projects: {e}")
        if _projects_cache["data"]:
            return _projects_cache["data"][:limit]
        return []


# Cache storage for uptime status
_uptime_cache = {"data": None, "timestamp": 0}
_uptime_ttl = 300  # 5 minutes cache


def get_uptime_status():
    """
    Get uptime status with caching (5 minute TTL).

    Returns:
        bool: True if services are up, False otherwise
    """
    global _uptime_cache
    current_time = datetime.datetime.now().timestamp()

    # Check if cache is valid
    if (
        _uptime_cache["data"] is not None
        and (current_time - _uptime_cache["timestamp"]) < _uptime_ttl
    ):
        return _uptime_cache["data"]

    # Fetch new data
    try:
        uptime = requests.get(
            "https://uptime.woodburn.au/api/status-page/main/badge", timeout=5
        )
        content = uptime.content.decode("utf-8").lower()
        status = "maintenance" in content or uptime.content.count(b"Up") > 1
        _uptime_cache = {"data": status, "timestamp": current_time}
        return status
    except Exception as e:
        print(f"Error fetching uptime: {e}")
        # Return cached or default (assume up)
        if _uptime_cache["data"] is not None:
            return _uptime_cache["data"]
        return True


# Cached wallet data loaders
@lru_cache(maxsize=1)
def get_wallet_tokens():
    """
    Get wallet tokens with caching.

    Returns:
        list: List of token dictionaries
    """
    try:
        with open(".well-known/wallets/.tokens") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading tokens: {e}")
        return []


@lru_cache(maxsize=1)
def get_coin_names():
    """
    Get coin names with caching.

    Returns:
        dict: Dictionary of coin names
    """
    try:
        with open(".well-known/wallets/.coins") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading coin names: {e}")
        return {}


@lru_cache(maxsize=1)
def get_wallet_domains():
    """
    Get wallet domains with caching.

    Returns:
        dict: Dictionary of wallet domains
    """
    try:
        if os.path.isfile(".well-known/wallets/.domains"):
            with open(".well-known/wallets/.domains") as file:
                return json.load(file)
    except Exception as e:
        print(f"Error loading domains: {e}")
    return {}
