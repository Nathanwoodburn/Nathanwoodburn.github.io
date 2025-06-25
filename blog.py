import os
from flask import render_template
from datetime import datetime
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from bs4 import BeautifulSoup
import re


def list_blog_page_files():
    blog_pages = os.listdir("data/blog")
    # Remove .md extension
    blog_pages = [page.removesuffix(".md") for page in blog_pages if page.endswith(".md")]

    return blog_pages


def render_blog_page(date,handshake_scripts=None):
    # Convert md to html
    if not os.path.exists(f"data/blog/{date}.md"):
        return render_template("404.html"), 404
    
    with open(f"data/blog/{date}.md", "r") as f:
        content = f.read()
    # Get the title from the file name
    title = date.removesuffix(".md").replace("_", " ")
    # Convert the md to html
    content = markdown.markdown(content, extensions=['sane_lists', 'codehilite', 'fenced_code'])
    # Add target="_blank" to all links
    content = content.replace('<a href="', '<a target="_blank" href="')

    content = content.replace("<h4", "<h4 style='margin-bottom:0px;'")

    content = fix_numbered_lists(content)

    return render_template(
        "blog/template.html",
        title=title,
        content=content,
        handshake_scripts=handshake_scripts,
    )


def fix_numbered_lists(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Find the <p> tag containing numbered steps
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        content = p.decode_contents()

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
                    ol_items.append(f"<li style='list-style: auto;'>{step_html}</li>")

            # Build the final list HTML
            ol_html = "<ol>\n" + "\n".join(ol_items) + "\n</ol>"

            # Rebuild paragraph with optional pre-text
            new_html = f"{pre_text}<br />\n{ol_html}" if pre_text else ol_html

            # Replace old <p> with parsed version
            new_fragment = BeautifulSoup(new_html, 'html.parser')
            p.replace_with(new_fragment)
            break  # Only process the first matching <p>

    return str(soup)


def render_blog_home(handshake_scripts=None):
    # Get a list of pages
    blog_pages = list_blog_page_files()
    # Create a html list of pages
    blog_pages = [
        f"""<li class="list-group-item">
        
            <p style="margin-bottom: 0px;"><a href='/blog/{page}'>{page.replace("_"," ")}</a></p>
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