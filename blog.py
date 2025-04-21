import os
from flask import render_template
from datetime import datetime
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension


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
    title = date.removesuffix(".md").replace("_", " ").title()
    # Convert the md to html
    content = markdown.markdown(content, extensions=['codehilite', 'fenced_code'])
    # Add target="_blank" to all links
    content = content.replace('<a href="', '<a target="_blank" href="')

    return render_template(
        "blog/template.html",
        title=title,
        content=content,
        handshake_scripts=handshake_scripts,
    )


    


def render_blog_home(handshake_scripts=None):
    # Get a list of pages
    blog_pages = list_blog_page_files()
    # Create a html list of pages
    blog_pages = [
        f"""<li class="list-group-item">
            <a href='/blog/{page}'>{page.replace("_"," ")}</a>
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