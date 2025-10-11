from flask import Blueprint, make_response
import requests

podcast_bp = Blueprint('podcast', __name__)

@podcast_bp.route("/ID1")
def podcast_index_get():
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1")
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@podcast_bp.route("/ID1/")
def podcast_contents_get():
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1/")
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@podcast_bp.route("/ID1/<path:path>")
def podcast_path_get(path):
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1/" + path)
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@podcast_bp.route("/ID1.xml")
def podcast_xml_get():
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1.xml")
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@podcast_bp.route("/podsync.opml")
def podcast_podsync_get():
    req = requests.get("https://podcasts.c.woodburn.au/podsync.opml")
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )