from flask import Blueprint, render_template, make_response, request, jsonify
import datetime
import os
from tools import getHandshakeScript, error_response, isCLI
from curl import get_header
from bs4 import BeautifulSoup
import re

# Create blueprint
app = Blueprint('now', __name__, url_prefix='/now')


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
        date = list_dates()[0]
        date = datetime.datetime.strptime(date, "%y_%m_%d")
        date = date.strftime("%A, %B %d, %Y")
        return date
    return list_dates()[0]


def render_latest(handshake_scripts=None):
    now_page = list_dates()[0]
    return render(now_page, handshake_scripts=handshake_scripts)


def render(date, handshake_scripts=None):
    # If the date is not available, render the latest page
    if date is None:
        return render_latest(handshake_scripts=handshake_scripts)
    # Remove .html
    date = date.removesuffix(".html")

    if date not in list_dates():
        return error_response(request)

    date_formatted = datetime.datetime.strptime(date, "%y_%m_%d")
    date_formatted = date_formatted.strftime("%A, %B %d, %Y")
    return render_template(f"now/{date}.html", DATE=date_formatted, handshake_scripts=handshake_scripts)

def render_curl(date=None):
    # If the date is not available, render the latest page
    if date is None:
        date = get_latest_date()

    # Remove .html if present
    date = date.removesuffix(".html")

    if date not in list_dates():
        return error_response(request)

    # Format the date nicely
    date_formatted = datetime.datetime.strptime(date, "%y_%m_%d")
    date_formatted = date_formatted.strftime("%A, %B %d, %Y")
    
    # Load HTML
    with open(f"templates/now/{date}.html", "r", encoding="utf-8") as f:
        raw_html = f.read().replace("{{ date }}", date_formatted)
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    posts = []

    # Find divs matching your pattern
    divs = soup.find_all("div", style=re.compile(r"max-width:\s*700px", re.IGNORECASE))

    for div in divs:
        # header could be h1/h2/h3 inside the div
        header_tag = div.find(["h1", "h2", "h3"])
        # content is usually one or more <p> tags inside the div
        p_tags = div.find_all("p")

        if header_tag and p_tags:
            header_text = header_tag.get_text(strip=True)
            content_lines = []

            for p in p_tags:
                # Extract text
                text = p.get_text(strip=False)

                # Extract any <a> links in the paragraph
                links = [a.get("href") for a in p.find_all("a", href=True)]
                if links:
                    text += "\nLinks: " + ", ".join(links)

                content_lines.append(text)

            content_text = "\n\n".join(content_lines)
            posts.append({"header": header_text, "content": content_text})

    # Build final response
    response = ""
    for post in posts:
        response += f"[1m{post['header']}[0m\n\n{post['content']}\n\n"

    return render_template("now.ascii", date=date_formatted, content=response, header=get_header())



@app.route("/")
def index():
    if isCLI(request):
        return render_curl()
    return render_latest(handshake_scripts=getHandshakeScript(request.host))


@app.route("/<path:path>")
def path(path):
    if isCLI(request):
        return render_curl(path)

    return render(path, handshake_scripts=getHandshakeScript(request.host))


@app.route("/old")
@app.route("/old/")
def old():
    now_dates = list_dates()[1:]
    if isCLI(request):
        response = ""
        for date in now_dates:
            link = date
            date_fmt = datetime.datetime.strptime(date, "%y_%m_%d")
            date_fmt = date_fmt.strftime("%A, %B %d, %Y")
            response += f"{date_fmt} - /now/{link}\n"
        return render_template("now.ascii", date="Old Now Pages", content=response, header=get_header())


    html = '<ul class="list-group">'
    html += f'<a style="text-decoration:none;" href="/now"><li class="list-group-item" style="background-color:#000000;color:#ffffff;">{get_latest_date(True)}</li></a>'

    for date in now_dates:
        link = date
        date = datetime.datetime.strptime(date, "%y_%m_%d")
        date = date.strftime("%A, %B %d, %Y")
        html += f'<a style="text-decoration:none;" href="/now/{link}"><li class="list-group-item" style="background-color:#000000;color:#ffffff;">{date}</li></a>'

    html += "</ul>"
    return render_template(
        "now/old.html", handshake_scripts=getHandshakeScript(request.host), now_pages=html
    )


@app.route("/now.rss")
@app.route("/now.xml")
@app.route("/rss.xml")
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


@app.route("/now.json")
def json():
    now_pages = list_page_files()
    host = "https://" + request.host
    if ":" in request.host:
        host = "http://" + request.host
    now_pages = [{"url": host+"/now/"+page.strip(".html"), "date": datetime.datetime.strptime(page.strip(".html"), "%y_%m_%d").strftime(
        "%A, %B %d, %Y"), "title": "What's Happening "+datetime.datetime.strptime(page.strip(".html"), "%y_%m_%d").strftime("%A, %B %d, %Y")} for page in now_pages]
    return jsonify(now_pages)
