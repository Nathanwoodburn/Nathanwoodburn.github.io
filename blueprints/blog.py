import json
import os
import re
from functools import lru_cache

import markdown
from bs4 import BeautifulSoup
from flask import Blueprint, jsonify, render_template, request

from tools import getClientIP, getHandshakeScript, isCLI

app = Blueprint("blog", __name__, url_prefix="/blog")

BLOG_DIR = "data/blog"


@lru_cache(maxsize=32)
def list_page_files():
    if not os.path.isdir(BLOG_DIR):
        return []
    blog_files = [f for f in os.listdir(BLOG_DIR) if f.endswith((".md", ".json"))]
    # Sort pages by modified time, newest first
    blog_files.sort(
        key=lambda x: os.path.getmtime(os.path.join(BLOG_DIR, x)), reverse=True
    )

    seen = set()
    slugs = []
    for f in blog_files:
        slug = f.rsplit(".", 1)[0]
        if slug not in seen:
            seen.add(slug)
            slugs.append(slug)

    return slugs


@lru_cache(maxsize=64)
def get_blog_post(slug):
    """Get and parse blog post from markdown or json."""
    slug = slug.removesuffix(".html").removesuffix(".md").removesuffix(".json")
    md_path = os.path.join(BLOG_DIR, f"{slug}.md")
    json_path = os.path.join(BLOG_DIR, f"{slug}.json")

    if os.path.isfile(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            raw = f.read()

        title = slug.replace("_", " ")
        date = ""
        description = ""
        content = raw

        # Parse frontmatter if present
        stripped_raw = raw.lstrip()
        if stripped_raw.startswith("---"):
            parts = stripped_raw.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                content = parts[2].strip()
                for line in frontmatter.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip().lower()
                        v = v.strip().strip("\"'")
                        if k == "title":
                            title = v
                        elif k == "date":
                            date = v
                        elif k == "description":
                            description = v

        if not description:
            for p in content.split("\n\n"):
                clean_p = p.strip()
                if not clean_p or clean_p.startswith(("#", "<", "```", "[View")):
                    continue
                snippet = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean_p)
                snippet = re.sub(r"[*_`]", "", snippet).strip()
                snippet = " ".join(snippet.split())
                if snippet and len(snippet) > 15:
                    description = (
                        (snippet[:150] + "...") if len(snippet) > 150 else snippet
                    )
                    break

        return {
            "title": title,
            "date": date,
            "description": description,
            "content": content,
            "raw": raw,
            "type": "md",
            "slug": slug,
        }

    elif os.path.isfile(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            raw = f.read()
        try:
            data = json.loads(raw)
            title = data.get("title", slug.replace("_", " "))
            content = data.get("content", "")
            date = data.get("date", "")
            description = data.get("description", "")
            return {
                "title": title,
                "date": date,
                "description": description,
                "content": content,
                "raw": raw,
                "type": "json",
                "slug": slug,
            }
        except json.JSONDecodeError:
            return None

    return None


@lru_cache(maxsize=64)
def render_markdown_to_html(content):
    """Convert markdown to HTML with caching."""
    html = markdown.markdown(
        content, extensions=["sane_lists", "codehilite", "fenced_code", "tables"]
    )
    # Add target="_blank" to all links
    html = re.sub(
        r'<a\s+(?![^>]*target=)(href="[^"]*")',
        r'<a target="_blank" \1',
        html,
    )
    html = html.replace("<h4", "<h4 style='margin-bottom:0px;'")
    html = fix_numbered_lists(html)
    return html


def fix_numbered_lists(html):
    soup = BeautifulSoup(html, "html.parser")

    # Find the <p> tag containing numbered steps
    paragraphs = soup.find_all("p")
    for p in paragraphs:
        content = p.decode_contents()  # type: ignore

        # Check for likely numbered step structure
        if re.search(r"1\.\s", content):
            # Split into pre-list and numbered steps
            # Match: <br>, optional whitespace, then a number and dot
            parts = re.split(r"(?:<br\s*/?>)?\s*(\d+)\.\s", content)

            # Result: [pre-text, '1', step1, '2', step2, ..., '10', step10]
            pre_text = parts[0].strip()
            steps = parts[1:]

            # Assemble the ordered list
            ol_items = []
            for i in range(0, len(steps), 2):
                if i + 1 < len(steps):
                    step_html = steps[i + 1].strip()
                    ol_items.append(f"<li style='list-style: auto;'>{step_html}</li>")

            # Build the final list HTML
            ol_html = "<ol>\n" + "\n".join(ol_items) + "\n</ol>"

            # Rebuild paragraph with optional pre-text
            new_html = f"{pre_text}<br />\n{ol_html}" if pre_text else ol_html

            # Replace old <p> with parsed version
            new_fragment = BeautifulSoup(new_html, "html.parser")
            p.replace_with(new_fragment)
            break  # Only process the first matching <p>

    return str(soup)


def render_page(slug, handshake_scripts=None):
    post = get_blog_post(slug)
    if post is None:
        return render_template("404.html"), 404

    # Convert the md to html (cached)
    html_content = render_markdown_to_html(post["content"])

    return render_template(
        "blog/template.html",
        title=post["title"],
        date=post["date"],
        description=post["description"],
        content=html_content,
        handshake_scripts=handshake_scripts,
        slug=post["slug"],
    )


def render_home(handshake_scripts: str | None = None):
    # Get a list of pages
    slugs = list_page_files()
    posts = [get_blog_post(s) for s in slugs if get_blog_post(s)]

    # Create a fallback html list of pages
    blog_items = []
    for p in posts:
        name = p["title"]
        slug = p["slug"]
        desc_html = (
            f'<br><small style="color:#aaaaaa;">{p["description"]}</small>'
            if p["description"]
            else ""
        )
        blog_items.append(
            f"""<a href='/blog/{slug}' class="blog-item-link" style="text-decoration: none; margin-bottom: 12px; display: block;">
            <li class="list-group-item blog-card" style="background-color: #000000; border: 1px solid #282828; border-radius: 8px; padding: 18px 24px; text-align: left; color: #ffffff;">
                <h4 style="margin: 0; color: #ffffff; font-size: 1.2rem;">{name}</h4>{desc_html}
            </li>
        </a>"""
        )

    blogs_html = "\n".join(blog_items)

    # Render the template
    return render_template(
        "blog/blog.html",
        posts=posts,
        blogs=blogs_html,
        handshake_scripts=handshake_scripts,
    )


@app.route("/", strict_slashes=False)
def index():
    if not isCLI(request):
        return render_home(handshake_scripts=getHandshakeScript(request.host))

    # Get a list of pages
    slugs = list_page_files()
    posts = [get_blog_post(s) for s in slugs if get_blog_post(s)]

    blog_pages = [
        {
            "name": p["title"],
            "url": f"/blog/{p['slug']}",
            "download": f"/blog/{p['slug']}.{p['type']}",
        }
        for p in posts
    ]

    # Render the template
    return jsonify(
        {
            "status": 200,
            "message": "Check out my various blog posts",
            "ip": getClientIP(request),
            "blogs": blog_pages,
        }
    ), 200


@app.route("/<path:path>")
def path(path):
    if path.endswith(".md"):
        post = get_blog_post(path.removesuffix(".md"))
        if post is None:
            return render_template("404.html"), 404
        return post["content"], 200, {"Content-Type": "text/plain; charset=utf-8"}

    if path.endswith(".json"):
        post = get_blog_post(path.removesuffix(".json"))
        if post is None:
            return render_template("404.html"), 404
        return jsonify(post), 200

    if not isCLI(request):
        return render_page(path, handshake_scripts=getHandshakeScript(request.host))

    # Get cached content
    post = get_blog_post(path)
    if post is None:
        return render_template("404.html"), 404

    return jsonify(
        {
            "status": 200,
            "message": f"Blog post: {post['title']}",
            "ip": getClientIP(request),
            "title": post["title"],
            "date": post["date"],
            "description": post["description"],
            "content": post["content"],
            "download": f"/blog/{post['slug']}.{post['type']}",
        }
    ), 200


@app.route("/<path:path>.md")
def path_md(path):
    post = get_blog_post(path)
    if post is None:
        return render_template("404.html"), 404

    # Return the raw markdown or content
    return post["content"], 200, {"Content-Type": "text/plain; charset=utf-8"}
