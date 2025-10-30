from flask import Blueprint, make_response, request
from tools import error_response
import requests

app = Blueprint('podcast', __name__)

@app.route("/ID1")
def index():
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1")
    if req.status_code != 200:
        return error_response(request, "Error from Podcast Server", req.status_code)

    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@app.route("/ID1/")
def contents():
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1/")
    if req.status_code != 200:
        return error_response(request, "Error from Podcast Server", req.status_code)
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@app.route("/ID1/<path:path>")
def path(path):
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1/" + path)
    if req.status_code != 200:
        return error_response(request, "Error from Podcast Server", req.status_code)
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@app.route("/ID1.xml")
def xml():
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1.xml")
    if req.status_code != 200:
        return error_response(request, "Error from Podcast Server", req.status_code)
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@app.route("/podsync.opml")
def podsync():
    req = requests.get("https://podcasts.c.woodburn.au/podsync.opml")
    if req.status_code != 200:
        return error_response(request, "Error from Podcast Server", req.status_code)
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )
