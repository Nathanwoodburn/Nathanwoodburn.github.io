import os
from flask import Blueprint, render_template, request, jsonify
import markdown
from bs4 import BeautifulSoup
import re
from functools import lru_cache
from tools import isCLI, getClientIP, getHandshakeScript

app = Blueprint('blog', __name__, url_prefix='/blog')


@lru_cache(maxsize=32)
def list_page_files():
    blog_pages = os.listdir("data/blog")
    # Sort pages by modified time, newest first
    blog_pages.sort(
        key=lambda x: os.path.getmtime(os.path.join("data/blog", x)), reverse=True)

    # Remove .md extension
    blog_pages = [page.removesuffix(".md")
                  for page in blog_pages if page.endswith(".md")]

    return blog_pages


@lru_cache(maxsize=64)
def get_blog_content(date):
    """Get and cache blog content."""
    if not os.path.exists(f"data/blog/{date}.md"):
        return None
    
    with open(f"data/blog/{date}.md", "r") as f:
        return f.read()


@lru_cache(maxsize=64)
def render_markdown_to_html(content):
    """Convert markdown to HTML with caching."""
    html = markdown.markdown(
        content, extensions=['sane_lists', 'codehilite', 'fenced_code'])
    # Add target="_blank" to all links
    html = html.replace('<a href="', '<a target="_blank" href="')
    html = html.replace("<h4", "<h4 style='margin-bottom:0px;'")
    html = fix_numbered_lists(html)
    return html


def render_page(date, handshake_scripts=None):
    # Get cached content
    content = get_blog_content(date)
    if content is None:
        return render_template("404.html"), 404

    # Get the title from the file name
    title = date.removesuffix(".md").replace("_", " ")
    # Convert the md to html (cached)
    html_content = render_markdown_to_html(content)

    return render_template(
        "blog/template.html",
        title=title,
        content=html_content,
        handshake_scripts=handshake_scripts,
    )


def fix_numbered_lists(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Find the <p> tag containing numbered steps
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        content = p.decode_contents()  # type: ignore

        # Check for likely numbered step structure
        if re.search(r'1\.\s', content):
            # Split into pre-list and numbered steps
            # Match: <br>, optional whitespace, then a number and dot
            parts = re.split(r'(?:<br\s*/?>)?\s*(\d+)\.\s', content)

            # Result: [pre-text, '1', step1, '2', step2, ..., '10', step10]
            pre_text = parts[0].strip()
            steps = parts[1:]

            # Assemble the ordered list
            ol_items = []
            for i in range(0, len(steps), 2):
                if i+1 < len(steps):
                    step_html = steps[i+1].strip()
                    ol_items.append(
                        f"<li style='list-style: auto;'>{step_html}</li>")

            # Build the final list HTML
            ol_html = "<ol>\n" + "\n".join(ol_items) + "\n</ol>"

            # Rebuild paragraph with optional pre-text
            new_html = f"{pre_text}<br />\n{ol_html}" if pre_text else ol_html

            # Replace old <p> with parsed version
            new_fragment = BeautifulSoup(new_html, 'html.parser')
            p.replace_with(new_fragment)
            break  # Only process the first matching <p>

    return str(soup)


def render_home(handshake_scripts: str | None = None):
    # Get a list of pages
    blog_pages = list_page_files()
    # Create a html list of pages
    blog_pages = [
        f"""<li class="list-group-item">
        
            <p style="margin-bottom: 0px;"><a href='/blog/{page}'>{page.replace("_", " ")}</a></p>
        </li>"""
        for page in blog_pages
    ]
    # Join the list
    blog_pages = "\n".join(blog_pages)
    # Render the template
    return render_template(
        "blog/blog.html",
        blogs=blog_pages,
        handshake_scripts=handshake_scripts,
    )


@app.route("/", strict_slashes=False)
def index():
    if not isCLI(request):
        return render_home(handshake_scripts=getHandshakeScript(request.host))

    # Get a list of pages
    blog_pages = list_page_files()
    # Create a html list of pages
    blog_pages = [
        {"name": page.replace("_", " "), "url": f"/blog/{page}", "download": f"/blog/{page}.md"} for page in blog_pages
    ]

    # Render the template
    return jsonify({
        "status": 200,
        "message": "Check out my various blog postsa",
        "ip": getClientIP(request),
        "blogs": blog_pages
    }), 200


@app.route("/<path:path>")
def path(path):
    if not isCLI(request):
        return render_page(path, handshake_scripts=getHandshakeScript(request.host))

    # Get cached content
    content = get_blog_content(path)
    if content is None:
        return render_template("404.html"), 404

    # Get the title from the file name
    title = path.replace("_", " ")
    return jsonify({
        "status": 200,
        "message": f"Blog post: {title}",
        "ip": getClientIP(request),
        "title": title,
        "content": content,
        "download": f"/blog/{path}.md"
    }), 200


@app.route("/<path:path>.md")
def path_md(path):
    content = get_blog_content(path)
    if content is None:
        return render_template("404.html"), 404

    # Return the raw markdown file
    return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
