from flask import Blueprint, render_template, make_response, request, jsonify
import datetime
import os

# Create blueprint
now_bp = Blueprint('now', __name__)

def list_page_files():
    now_pages = os.listdir("templates/now")
    now_pages = [
        page for page in now_pages if page != "template.html" and page != "old.html"
    ]
    now_pages.sort(reverse=True)
    return now_pages

def list_dates():
    now_pages = list_page_files()
    now_dates = [page.split(".")[0] for page in now_pages]
    return now_dates

def get_latest_date(formatted=False):
    if formatted:
        date=list_dates()[0]
        date = datetime.datetime.strptime(date, "%y_%m_%d")
        date = date.strftime("%A, %B %d, %Y")
        return date
    return list_dates()[0]

def render_latest(handshake_scripts=None):
    now_page = list_dates()[0]
    return render(now_page,handshake_scripts=handshake_scripts)

def render(date,handshake_scripts=None):
    # If the date is not available, render the latest page
    if date is None:
        return render_latest(handshake_scripts=handshake_scripts)
    # Remove .html
    date = date.removesuffix(".html")

    if date not in list_dates():
        return render_template("404.html"), 404


    date_formatted = datetime.datetime.strptime(date, "%y_%m_%d")
    date_formatted = date_formatted.strftime("%A, %B %d, %Y")
    return render_template(f"now/{date}.html",DATE=date_formatted,handshake_scripts=handshake_scripts)

@now_bp.route("/")
def index():
    handshake_scripts = ''
    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""
    else:
        handshake_scripts = '<script src="https://nathan.woodburn/handshake.js" domain="nathan.woodburn" async></script><script src="https://nathan.woodburn/https.js" async></script>'

    return render_latest(handshake_scripts)


@now_bp.route("/<path:path>")
def path(path):
    handshake_scripts = ''
    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""
    else:
        handshake_scripts = '<script src="https://nathan.woodburn/handshake.js" domain="nathan.woodburn" async></script><script src="https://nathan.woodburn/https.js" async></script>'

    return render(path, handshake_scripts)


@now_bp.route("/old")
@now_bp.route("/old/")
def old():
    handshake_scripts = ''
    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""
    else:
        handshake_scripts = '<script src="https://nathan.woodburn/handshake.js" domain="nathan.woodburn" async></script><script src="https://nathan.woodburn/https.js" async></script>'

    now_dates = list_dates()[1:]
    html = '<ul class="list-group">'
    html += f'<a style="text-decoration:none;" href="/now"><li class="list-group-item" style="background-color:#000000;color:#ffffff;">{get_latest_date(True)}</li></a>'

    for date in now_dates:
        link = date
        date = datetime.datetime.strptime(date, "%y_%m_%d")
        date = date.strftime("%A, %B %d, %Y")
        html += f'<a style="text-decoration:none;" href="/now/{link}"><li class="list-group-item" style="background-color:#000000;color:#ffffff;">{date}</li></a>'

    html += "</ul>"
    return render_template(
        "now/old.html", handshake_scripts=handshake_scripts, now_pages=html
    )


@now_bp.route("/now.rss")
@now_bp.route("/now.xml")
@now_bp.route("/rss.xml")
def rss():
    host = "https://" + request.host
    if ":" in request.host:
        host = "http://" + request.host
    # Generate RSS feed
    now_pages = list_page_files()
    rss = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Nathan.Woodburn/</title><link>{host}</link><description>See what I\'ve been up to</description><language>en-us</language><lastBuildDate>{datetime.datetime.now(tz=datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")}</lastBuildDate><atom:link href="{host}/now.rss" rel="self" type="application/rss+xml" />'
    for page in now_pages:
        link = page.strip(".html")
        date = datetime.datetime.strptime(link, "%y_%m_%d")
        date = date.strftime("%A, %B %d, %Y")
        rss += f'<item><title>What\'s Happening {date}</title><link>{host}/now/{link}</link><description>Latest updates for {date}</description><guid>{host}/now/{link}</guid></item>'
    rss += "</channel></rss>"
    return make_response(rss, 200, {"Content-Type": "application/rss+xml"})


@now_bp.route("/now.json")
def json():
    now_pages = list_page_files()
    host = "https://" + request.host
    if ":" in request.host:
        host = "http://" + request.host
    now_pages = [{"url": host+"/now/"+page.strip(".html"), "date": datetime.datetime.strptime(page.strip(".html"), "%y_%m_%d").strftime(
        "%A, %B %d, %Y"), "title": "What's Happening "+datetime.datetime.strptime(page.strip(".html"), "%y_%m_%d").strftime("%A, %B %d, %Y")} for page in now_pages]
    return jsonify(now_pages)
