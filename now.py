import os
from flask import render_template
from datetime import datetime

def list_now_page_files():
    now_pages = os.listdir("templates/now")
    now_pages = [
        page for page in now_pages if page != "template.html" and page != "old.html"
    ]
    now_pages.sort(reverse=True)
    return now_pages

def list_now_dates():
    now_pages = list_now_page_files()
    now_dates = [page.split(".")[0] for page in now_pages]
    return now_dates

def get_latest_now_date(formatted=False):
    if formatted:
        date=list_now_dates()[0]
        date = datetime.strptime(date, "%y_%m_%d")
        date = date.strftime("%A, %B %d, %Y")
        return date
    return list_now_dates()[0]

def render_now_page(date,handshake_scripts=None):
    # If the date is not available, render the latest page
    if date is None:
        return render_latest_now(handshake_scripts=handshake_scripts)
    # Remove .html
    date = date.removesuffix(".html")

    if date not in list_now_dates():
        return render_template("404.html"), 404


    date_formatted = datetime.strptime(date, "%y_%m_%d")
    date_formatted = date_formatted.strftime("%A, %B %d, %Y")
    return render_template(f"now/{date}.html",DATE=date_formatted,handshake_scripts=handshake_scripts)

def render_latest_now(handshake_scripts=None):
    now_page = list_now_dates()[0]
    return render_now_page(now_page,handshake_scripts=handshake_scripts)
