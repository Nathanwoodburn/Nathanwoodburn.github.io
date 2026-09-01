import datetime
import json
import os
import re
from functools import lru_cache

import markdown
from bs4 import BeautifulSoup
from flask import Blueprint, jsonify, make_response, render_template, request

from curl import MAX_WIDTH, get_header
from tools import error_response, getHandshakeScript, isCLI

# Create blueprint
app = Blueprint("now", __name__, url_prefix="/")

NOW_DIR = "data/now"


@lru_cache(maxsize=16)
def list_page_files():
    if not os.path.isdir(NOW_DIR):
        return []
    now_pages = [
        page for page in os.listdir(NOW_DIR) if page.endswith((".md", ".json"))
    ]
    now_pages.sort(reverse=True)
    return now_pages


@lru_cache(maxsize=16)
def list_dates():
    now_pages = list_page_files()
    now_dates = []
    seen = set()
    for page in now_pages:
        date_name = page.rsplit(".", 1)[0]
        if date_name not in seen:
            seen.add(date_name)
            now_dates.append(date_name)
    now_dates.sort(reverse=True)
    return now_dates


@lru_cache(maxsize=8)
def get_latest_date(formatted=False):
    dates = list_dates()
    if not dates:
        return ""
    if formatted:
        date_str = dates[0]
        try:
            dt = datetime.datetime.strptime(date_str, "%y_%m_%d").replace(
                tzinfo=datetime.UTC
            )
            return dt.strftime("%A, %B %d, %Y")
        except ValueError:
            return date_str
    return dates[0]


@lru_cache(maxsize=64)
def get_now_raw_content(date):
    """Get raw file content and type (md or json)."""
    date = date.removesuffix(".html").removesuffix(".md").removesuffix(".json")
    md_path = os.path.join(NOW_DIR, f"{date}.md")
    json_path = os.path.join(NOW_DIR, f"{date}.json")

    if os.path.isfile(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            return f.read(), "md"
    elif os.path.isfile(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return f.read(), "json"
    return None, None


@lru_cache(maxsize=64)
def render_markdown_to_html(content):
    """Convert markdown to HTML with caching."""
    html = markdown.markdown(
        content, extensions=["sane_lists", "codehilite", "fenced_code", "tables"]
    )
    # Add target="_blank" to all external links
    html = re.sub(
        r'<a\s+(?![^>]*target=)(href="[^"]*")',
        r'<a target="_blank" \1',
        html,
    )
    html = html.replace("<h4", "<h4 style='margin-bottom:0px;'")
    return html


@lru_cache(maxsize=64)
def parse_now_sections(date):
    """Parse now page into a list of section dicts: [{'title': ..., 'content': html, 'content_md': md}]."""
    raw_content, content_type = get_now_raw_content(date)
    if raw_content is None:
        return []

    sections = []

    if content_type == "json":
        try:
            data = json.loads(raw_content)
            if isinstance(data, list):
                raw_sections = data
            elif isinstance(data, dict) and "sections" in data:
                raw_sections = data["sections"]
            elif isinstance(data, dict):
                raw_sections = [data]
            else:
                raw_sections = []

            for item in raw_sections:
                title = item.get("title", "")
                content_text = item.get("content", "")
                content_html = render_markdown_to_html(content_text)
                sections.append(
                    {
                        "title": title,
                        "content": content_html,
                        "content_md": content_text,
                    }
                )
        except json.JSONDecodeError:
            return []
    else:
        # Markdown file
        lines = raw_content.splitlines()
        current_title = ""
        current_lines = []

        for line in lines:
            if re.match(r"^#{1,2}\s+", line):
                if current_title or current_lines:
                    content_md = "\n".join(current_lines).strip()
                    sections.append(
                        {
                            "title": current_title,
                            "content": render_markdown_to_html(content_md),
                            "content_md": content_md,
                        }
                    )
                current_title = re.sub(r"^#{1,2}\s+", "", line).strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_title or current_lines:
            content_md = "\n".join(current_lines).strip()
            sections.append(
                {
                    "title": current_title,
                    "content": render_markdown_to_html(content_md),
                    "content_md": content_md,
                }
            )

    return sections


def render_latest(handshake_scripts=None):
    dates = list_dates()
    if not dates:
        return error_response(request)
    return render_page(dates[0], handshake_scripts=handshake_scripts)


def render_page(date, handshake_scripts=None):
    if date is None:
        return render_latest(handshake_scripts=handshake_scripts)

    date = date.removesuffix(".html").removesuffix(".md").removesuffix(".json")

    if date not in list_dates():
        return error_response(request)

    try:
        dt = datetime.datetime.strptime(date, "%y_%m_%d").replace(tzinfo=datetime.UTC)
        date_formatted = dt.strftime("%A, %B %d, %Y")
    except ValueError:
        date_formatted = date

    sections = parse_now_sections(date)

    return render_template(
        "now/template.html",
        DATE=date_formatted,
        sections=sections,
        handshake_scripts=handshake_scripts,
        date_slug=date,
    )


def render_curl(date=None):
    if date is None:
        date = get_latest_date()

    date = date.removesuffix(".html").removesuffix(".md").removesuffix(".json")

    if date not in list_dates():
        return error_response(request)

    try:
        dt = datetime.datetime.strptime(date, "%y_%m_%d").replace(tzinfo=datetime.UTC)
        date_formatted = dt.strftime("%A, %B %d, %Y")
    except ValueError:
        date_formatted = date

    sections = parse_now_sections(date)
    if not sections:
        return error_response(request, message="No content found for CLI rendering.")

    posts = []
    for section in sections:
        header_text = section["title"]
        soup = BeautifulSoup(section["content"], "html.parser")

        content_lines = []
        p_tags = soup.find_all(["p", "li", "tr"])
        if not p_tags:
            p_tags = [soup]

        for p in p_tags:
            text = p.get_text(strip=False).strip()
            if not text:
                continue

            links = [
                a.get("href")
                for a in p.find_all("a", href=True)
                if not a.get("href", "").startswith("#")
            ]

            wrapped_lines = []
            for line in text.splitlines():
                while len(line) > MAX_WIDTH:
                    split_at = line.rfind(" ", 0, MAX_WIDTH)
                    if split_at == -1:
                        split_at = MAX_WIDTH
                    wrapped_lines.append(line[:split_at].rstrip())
                    line = line[split_at:].lstrip()
                wrapped_lines.append(line)
            wrapped_text = "\n".join(wrapped_lines)

            if links:
                wrapped_text += "\nLinks: " + ", ".join(links)

            content_lines.append(wrapped_text)

        content_text = "\n\n".join(content_lines)
        posts.append({"header": header_text, "content": content_text})

    response = ""
    for post in posts:
        header = post["header"]
        content = post["content"]
        if header:
            response += f"\x1b[1m{header}\x1b[0m\n\n{content}\n\n"
        else:
            response += f"{content}\n\n"

    return render_template(
        "now.ascii", date=date_formatted, content=response, header=get_header()
    )


@app.route("/now", strict_slashes=False)
def index():
    if isCLI(request):
        return render_curl()
    return render_latest(handshake_scripts=getHandshakeScript(request.host))


@app.route("/now/old", strict_slashes=False)
@app.route("/old", strict_slashes=False)
def old():
    dates = list_dates()
    now_dates = dates[1:] if len(dates) > 1 else []

    if isCLI(request):
        response = ""
        for date in now_dates:
            try:
                date_fmt = datetime.datetime.strptime(date, "%y_%m_%d").replace(
                    tzinfo=datetime.UTC
                )
                date_str = date_fmt.strftime("%A, %B %d, %Y")
            except ValueError:
                date_str = date
            response += f"{date_str} - /now/{date}\n"
        return render_template(
            "now.ascii", date="Old Now Pages", content=response, header=get_header()
        )

    html = '<ul class="list-group">'
    html += f'<a style="text-decoration:none;" href="/now"><li class="list-group-item" style="background-color:#000000;color:#ffffff;">{get_latest_date(True)}</li></a>'

    for date in now_dates:
        try:
            parsed_date = datetime.datetime.strptime(date, "%y_%m_%d").replace(
                tzinfo=datetime.UTC
            )
            formatted_date = parsed_date.strftime("%A, %B %d, %Y")
        except ValueError:
            formatted_date = date
        html += f'<a style="text-decoration:none;" href="/now/{date}"><li class="list-group-item" style="background-color:#000000;color:#ffffff;">{formatted_date}</li></a>'

    html += "</ul>"
    return render_template(
        "now/old.html",
        handshake_scripts=getHandshakeScript(request.host),
        now_pages=html,
    )


@app.route("/now/<path:path>")
def path(path):
    if path.endswith(".md"):
        date = path.removesuffix(".md")
        content, _ = get_now_raw_content(date)
        if content is None:
            return error_response(request, code=404)
        return content, 200, {"Content-Type": "text/plain; charset=utf-8"}

    if path.endswith(".json") and path != "now.json":
        date = path.removesuffix(".json")
        sections = parse_now_sections(date)
        if not sections:
            return error_response(request, code=404)
        return jsonify(sections)

    if isCLI(request):
        return render_curl(path)

    return render_page(path, handshake_scripts=getHandshakeScript(request.host))


@app.route("/now.rss")
@app.route("/now.xml")
@app.route("/rss.xml")
def rss():
    host = "https://" + request.host
    path = request.path
    if ":" in request.host:
        host = "http://" + request.host

    now_dates = list_dates()

    build_date = datetime.datetime.now(tz=datetime.UTC).strftime(
        "%a, %d %b %Y %H:%M:%S %z"
    )

    rss_xml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
        f"<channel>"
        f"<title>Nathan.Woodburn/</title>"
        f"<link>{host}</link>"
        f"<description>See what I've been up to</description>"
        f"<language>en-us</language>"
        f"<lastBuildDate>{build_date}</lastBuildDate>"
        f'<atom:link href="{host}{path}" rel="self" type="application/rss+xml" />'
    )

    for link in now_dates:
        try:
            dt = datetime.datetime.strptime(link, "%y_%m_%d").replace(
                tzinfo=datetime.UTC
            )
            pubdate = dt.strftime("%a, %d %b %Y 00:00:00 +0000")
            formatted_date = dt.strftime("%A, %B %d, %Y")
        except ValueError:
            pubdate = build_date
            formatted_date = link

        rss_xml += f"""
        <item>
          <title>What's Happening {formatted_date}</title>
          <link>{host}/now/{link}</link>
          <description>Latest updates for {formatted_date}</description>
          <pubDate>{pubdate}</pubDate>
          <guid isPermaLink="true">{host}/now/{link}</guid>
        </item>
        """

    rss_xml += "</channel></rss>"
    return make_response(rss_xml, 200, {"Content-Type": "application/rss+xml"})


@app.route("/now.json")
def json_endpoint():
    now_dates = list_dates()
    host = "https://" + request.host
    if ":" in request.host:
        host = "http://" + request.host

    formatted_pages = []
    for page_name in now_dates:
        try:
            parsed_dt = datetime.datetime.strptime(page_name, "%y_%m_%d").replace(
                tzinfo=datetime.UTC
            )
            formatted_date = parsed_dt.strftime("%A, %B %d, %Y")
        except ValueError:
            formatted_date = page_name

        formatted_pages.append(
            {
                "url": f"{host}/now/{page_name}",
                "date": formatted_date,
                "title": f"What's Happening {formatted_date}",
            }
        )

    return jsonify(formatted_pages)
