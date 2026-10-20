import contextlib
import datetime
import json
import os
import re
import shutil
import subprocess
from functools import lru_cache

import jinja2
from dateutil.parser import parse
from flask import Request, jsonify, make_response, render_template

# HTTP status codes
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404

CRAWLERS = [
    "Googlebot",
    "Bingbot",
    "Chrome-Lighthouse",
    "Slurp",
    "DuckDuckBot",
    "Baiduspider",
    "YandexBot",
    "Sogou",
    "Exabot",
    "facebot",
    "ia_archiver",
    "Twitterbot",
]

CLI_AGENTS = ["curl", "hurl", "xh", "Posting", "HTTPie", "nushell"]

MAX_WIDTH = 80
ANSI_REGEX = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def visible_len(s: str) -> int:
    """Calculate visible character length of a string, ignoring ANSI escape codes."""
    return len(ANSI_REGEX.sub("", s))


def get_terminal_width(request=None, default: int = MAX_WIDTH) -> int:
    """Determine terminal column width from request query param or local terminal size."""
    if request is not None:
        val = request.args.get("width") or request.args.get("cols")
        if val and val.isdigit():
            w = int(val)
            if 40 <= w <= 240:
                return w
        return default

    with contextlib.suppress(OSError, ValueError):
        cols = shutil.get_terminal_size((default, 24)).columns
        if 40 <= cols <= 240:
            return cols

    return default


def wrap_line(line: str, width: int = MAX_WIDTH) -> list[str]:
    """Wrap a single line of text (preserving ANSI codes and bullet indentations) to width."""
    if visible_len(line) <= width:
        return [line]

    # Detect bullet or indented list prefix
    match_bullet = re.match(r"^(\s*[•\*\-]\s+)(.*)$", line)
    if match_bullet:
        prefix = match_bullet.group(1)
        content = match_bullet.group(2)
        subsequent_indent = " " * visible_len(prefix)
    else:
        match_spaces = re.match(r"^(\s+)(.*)$", line)
        if match_spaces:
            prefix = match_spaces.group(1)
            content = match_spaces.group(2)
            subsequent_indent = prefix
        else:
            prefix = ""
            content = line
            subsequent_indent = ""

    words = content.split(" ")
    wrapped_lines: list[str] = []
    current_line = prefix

    for word in words:
        if not word and current_line != prefix and current_line != subsequent_indent:
            cand = current_line + " "
        elif current_line == prefix or current_line == subsequent_indent:
            cand = current_line + word
        else:
            cand = current_line + " " + word

        if visible_len(cand) <= width:
            current_line = cand
        else:
            if current_line.strip():
                wrapped_lines.append(current_line)
            current_line = subsequent_indent + word

    if current_line.strip():
        wrapped_lines.append(current_line)

    return wrapped_lines or [line]


def wrap_ascii_text(text: str, width: int = MAX_WIDTH) -> str:
    """Wrap multi-line text (preserving ANSI codes) to a maximum terminal column width."""
    lines = text.splitlines()
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(wrap_line(line, width=width))
    result = "\n".join(wrapped)
    if text.endswith("\n"):
        result += "\n"
    return result


def getClientIP(request: Request) -> str:
    """
    Get the client's IP address from the request.

    Args:
        request (Request): The Flask request object

    Returns:
        str: The client's IP address
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.remote_addr
    if ip is None:
        ip = "unknown"
    return ip


@lru_cache(maxsize=1)
def getGitCommit() -> str:
    """
    Get the current git commit hash.

    Returns:
        str: The current git commit hash or a failure message
    """
    # if .git exists, get the latest commit hash
    if os.path.isdir(".git"):
        git_dir = ".git"
        head_ref = ""
        with open(os.path.join(git_dir, "HEAD")) as file:
            head_ref = file.read().strip()
        if head_ref.startswith("ref: "):
            head_ref = head_ref[5:]
            with open(os.path.join(git_dir, head_ref)) as file:
                return file.read().strip()
        else:
            return head_ref

    # Check if env SOURCE_COMMIT is set
    if "SOURCE_COMMIT" in os.environ:
        return os.environ["SOURCE_COMMIT"]

    return "failed to get version"


def isCLI(request: Request) -> bool:
    """
    Check if the request is from curl or hurl.

    Args:
        request (Request): The Flask request object

    Returns:
        bool: True if the request is from curl or hurl, False otherwise
    """
    if request.headers and request.headers.get("User-Agent"):
        user_agent = request.headers.get("User-Agent", "")
        return any(agent in user_agent for agent in CLI_AGENTS)
    return False


def isFinger(request: Request) -> bool:
    """
    Check if the request is a finger request.

    Args:
        request (Request): The Flask request object

    Returns:
        bool: True if the request is a finger request, False otherwise
    """
    if request.headers and request.headers.get("User-Agent"):
        user_agent = request.headers.get("User-Agent", "")
        return "finger" in user_agent.lower()
    return False


def isCrawler(request: Request) -> bool:
    """
    Check if the request is from a web crawler (e.g., Googlebot, Bingbot).

    Args:
        request (Request): The Flask request object

    Returns:
        bool: True if the request is from a web crawler, False otherwise
    """
    if request.headers and request.headers.get("User-Agent"):
        user_agent = request.headers.get("User-Agent", "")
        return any(crawler in user_agent for crawler in CRAWLERS)
    return False


@lru_cache(maxsize=128)
def isDev(host: str) -> bool:
    """
    Check if the host indicates a development environment.

    Args:
        host (str): The host string from the request

    Returns:
        bool: True if in development environment, False otherwise
    """
    return (
        host == "localhost:5000"
        or host == "127.0.0.1:5000"
        or os.getenv("DEV") == "true"
        or host == "test.nathan.woodburn.au"
    )


@lru_cache(maxsize=128)
def getHandshakeScript(host: str) -> str:
    """
    Get the handshake script HTML snippet.

    Args:
        host (str): The host string from the request

    Returns:
        str: The handshake script HTML snippet
    """
    return ""
    # if isDev(host):
    #     return ""
    # return '<script src="https://nathan.woodburn/handshake.js" domain="nathan.woodburn" async></script><script src="https://nathan.woodburn/https.js" async></script>'


@lru_cache(maxsize=64)
def getAddress(coin: str) -> str:
    """
    Get the wallet address for a cryptocurrency.

    Args:
        coin (str): The cryptocurrency code

    Returns:
        str: The wallet address or empty string if not found
    """
    address = ""
    wallet_path = f".well-known/wallets/{coin.upper()}"
    if os.path.isfile(wallet_path):
        with open(wallet_path) as file:
            address = file.read()
    return address


@lru_cache(maxsize=256)
def getFilePath(name: str, path: str) -> str | None:
    """
    Find a file in a directory tree, searching non-external directories first.

    Args:
        name (str): The filename to find
        path (str): The root directory to search

    Returns:
        Optional[str]: The full path to the file or None if not found
    """
    external_dir = os.path.abspath(os.path.join(path, "assets", "img", "external"))

    # 1. Search in non-external directories first
    for root, dirs, files in os.walk(path):
        root_abs = os.path.abspath(root)
        if root_abs == external_dir or root_abs.startswith(external_dir + os.sep):
            continue
        if name in files:
            return os.path.join(root, name)

    # 2. Search external directory if not found in any other directory
    if os.path.isdir(external_dir):
        for root, dirs, files in os.walk(external_dir):
            if name in files:
                return os.path.join(root, name)

    return None


def json_response(
    request: Request, message: str | dict = "404 Not Found", code: int = 404
):
    """
    Create a JSON response with standard formatting.

    Args:
        request (Request): The Flask request object
        message (Union[str, Dict]): The response message or data
        code (int): The HTTP status code

    Returns:
        Tuple[Dict, int]: The JSON response and HTTP status code
    """
    if isinstance(message, dict):
        # Add status and ip to dict
        message["status"] = code
        message["ip"] = getClientIP(request)
        return jsonify(message), code

    return jsonify(
        {
            "status": code,
            "message": message,
            "ip": getClientIP(request),
        }
    ), code


def error_response(
    request: Request,
    message: str = "404 Not Found",
    code: int = 404,
    force_json: bool = False,
) -> tuple[dict, int] | object:
    """
    Create an error response in JSON or HTML format.

    Args:
        request (Request): The Flask request object
        message (str): The error message
        code (int): The HTTP status code
        force_json (bool): Whether to force JSON response regardless of client

    Returns:
        Union[Tuple[Dict, int], object]: The JSON or HTML response
    """
    if force_json or isCLI(request):
        return json_response(request, message, code)

    # Check if <error code>.html exists in templates
    template_name = (
        f"{code}.html" if os.path.isfile(f"templates/{code}.html") else "404.html"
    )
    response = make_response(
        render_template(template_name, code=code, message=message), code
    )

    # Add message to response headers
    response.headers["X-Error-Message"] = message
    return response


def parse_date(date_groups: list[str]) -> str | None:
    """
    Parse a list of date components into YYYY-MM-DD format.
    Uses dateutil.parser for robust parsing.
    Works for:
      - DD Month YYYY
      - Month DD, YYYY
      - YYYY-MM-DD
      - YYYYMMDD
      - Month YYYY (defaults day to 1)
      - Handles ordinal suffixes (st, nd, rd, th)
    """
    try:
        # Join date groups into a single string
        date_str = " ".join(date_groups).strip()

        # Remove ordinal suffixes
        date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str, flags=re.IGNORECASE)

        # Parse with dateutil, default day=1 if missing
        dt = parse(date_str, default=datetime.datetime(1900, 1, 1, tzinfo=datetime.UTC))

        # If year is missing, parse will fallback to 1900 → reject
        if dt.year == 1900:
            return None

        return dt.strftime("%Y-%m-%d")

    except (ValueError, TypeError):
        return None


def get_tools_data():
    with open("data/tools.json", "r") as f:
        return json.load(f)


def find_chromium() -> str | None:
    """Find available chromium/chrome binary for headless PDF generation."""
    for cmd in ["chromium", "chromium-browser", "google-chrome", "chrome"]:
        path = shutil.which(cmd)
        if path:
            return path
    for p in [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ]:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def parse_support_arg(req) -> bool:
    """
    Check if the support query parameter is set on the request.
    Handles ?support, ?support=1, ?support=true, ?support=yes.
    """
    if not req or not req.args:
        return False
    val = req.args.get("support")
    if val is None:
        return False
    if val == "":
        return True
    return str(val).lower().strip() in ("1", "true", "yes", "support")


def get_resume_data(support: bool = False) -> dict:
    """Load and prepare resume data from data/resume.json."""
    with open("data/resume.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("titles", {}).get(
        "support" if support else "default", data.get("title", "")
    )
    summary = data.get("summaries", {}).get(
        "support" if support else "default", data.get("summary", "")
    )

    return {
        **data,
        "active_title": title,
        "active_summary": summary,
        "is_support": support,
    }


def get_resume_md(support: bool = False, resume_data: dict | None = None) -> str:
    """Generate a clean Markdown representation of the resume."""
    if resume_data is None:
        resume_data = get_resume_data(support=support)

    lines = []
    lines.append(f"# {resume_data.get('name', 'Nathan Woodburn')}")
    active_title = resume_data.get("active_title", "")
    if active_title:
        lines.append(f"### {active_title}\n")

    # Contact
    contact_parts = []
    for item in resume_data.get("contact", []):
        label = item.get("label") or ""
        url = item.get("url")
        if url:
            contact_parts.append(f"[{label}]({url})")
        elif label:
            contact_parts.append(label)
    if contact_parts:
        lines.append(" • ".join(contact_parts) + "\n")

    # Summary
    summary = resume_data.get("active_summary", "")
    if summary:
        lines.append("## Summary\n")
        lines.append(f"{summary}\n")

    # Experience
    experience = resume_data.get("experience", [])
    if experience:
        lines.append("## Experience\n")
        for job in experience:
            role = job.get("role", "")
            company = job.get("company", "")
            location = job.get("location")
            dates = job.get("dates")

            header_parts = [p for p in [role, company] if p]
            lines.append(f"### {' — '.join(header_parts)}")

            meta_parts = [p for p in [dates, location] if p]
            if meta_parts:
                lines.append(f"*{' | '.join(meta_parts)}*")

            for bullet in job.get("bullets", []):
                lines.append(f"- {bullet}")
            lines.append("")

    # Projects
    projects = resume_data.get("projects", [])
    if projects:
        lines.append("## Projects\n")
        for proj in projects:
            name = proj.get("name", "")
            tech = proj.get("technologies")
            lines.append(f"### {name}")
            if tech:
                lines.append(f"*Technologies: {tech}*")
            for bullet in proj.get("bullets", []):
                lines.append(f"- {bullet}")
            lines.append("")

    # Education
    education = resume_data.get("education", [])
    if education:
        lines.append("## Education\n")
        for edu in education:
            degree = edu.get("degree", "")
            inst = edu.get("institution", "")
            dates = edu.get("dates")
            desc = edu.get("description")

            header_parts = [p for p in [degree, inst] if p]
            lines.append(f"### {' — '.join(header_parts)}")
            if dates:
                lines.append(f"*{dates}*")
            if desc:
                lines.append(f"- {desc}")
            lines.append("")

    # Skills
    skills = resume_data.get("skills", [])
    if skills:
        lines.append("## Skills\n")
        for skill in skills:
            lines.append(f"- {skill}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def get_resume_txt(
    support: bool = False,
    resume_data: dict | None = None,
    width: int = MAX_WIDTH,
) -> str:
    """Generate a clean plain text representation of the resume."""
    if resume_data is None:
        resume_data = get_resume_data(support=support)

    divider = "=" * width
    sub_divider = "-" * width

    lines = [divider]
    lines.append(resume_data.get("name", "Nathan Woodburn").upper())
    active_title = resume_data.get("active_title", "")
    if active_title:
        lines.append(active_title)
    lines.append(divider)
    lines.append("")

    # Contact
    contact = resume_data.get("contact", [])
    if contact:
        lines.append("CONTACT")
        lines.append(sub_divider)
        for item in contact:
            c_type = (item.get("type") or "Info").capitalize()
            label = item.get("label") or ""
            url = item.get("url")
            val = (
                label
                if (not url or url.startswith(("tel:", "mailto:")))
                else (f"{label} ({url})" if label != url else url)
            )
            lines.extend(wrap_line(f"{c_type + ':':<11} {val}", width=width))
        lines.append("")

    # Summary
    summary = resume_data.get("active_summary", "")
    if summary:
        lines.append("SUMMARY")
        lines.append(sub_divider)
        lines.extend(wrap_line(summary, width=width))
        lines.append("")

    # Experience
    experience = resume_data.get("experience", [])
    if experience:
        lines.append("EXPERIENCE")
        lines.append(sub_divider)
        for job in experience:
            role = job.get("role", "")
            company = job.get("company", "")
            location = job.get("location")
            dates = job.get("dates")

            role_company = f"{role} — {company}" if company else role
            meta = " | ".join([p for p in [dates, location] if p])
            lines.extend(wrap_line(role_company, width=width))
            if meta:
                lines.append(meta)
            for bullet in job.get("bullets", []):
                lines.extend(wrap_line(f"  * {bullet}", width=width))
            lines.append("")

    # Projects
    projects = resume_data.get("projects", [])
    if projects:
        lines.append("PROJECTS")
        lines.append(sub_divider)
        for proj in projects:
            name = proj.get("name", "")
            tech = proj.get("technologies")
            p_header = f"{name} ({tech})" if tech else name
            lines.extend(wrap_line(p_header, width=width))
            for bullet in proj.get("bullets", []):
                lines.extend(wrap_line(f"  * {bullet}", width=width))
            lines.append("")

    # Education
    education = resume_data.get("education", [])
    if education:
        lines.append("EDUCATION")
        lines.append(sub_divider)
        for edu in education:
            degree = edu.get("degree", "")
            inst = edu.get("institution", "")
            dates = edu.get("dates")
            desc = edu.get("description")

            deg_inst = f"{degree} — {inst}" if inst else degree
            lines.extend(wrap_line(deg_inst, width=width))
            if dates:
                lines.append(dates)
            if desc:
                lines.extend(wrap_line(f"  * {desc}", width=width))
            lines.append("")

    # Skills
    skills = resume_data.get("skills", [])
    if skills:
        lines.append("SKILLS")
        lines.append(sub_divider)
        for skill in skills:
            lines.append(f"  * {skill}")
        lines.append("")

    lines.append(divider)
    return "\n".join(lines).strip() + "\n"


def get_resume_ascii(
    support: bool = False,
    header: str | None = None,
    resume_data: dict | None = None,
    width: int | None = None,
) -> str:
    """Generate the CLI ASCII/ANSI terminal representation of the resume."""
    if resume_data is None:
        resume_data = get_resume_data(support=support)

    if header is None:
        if os.path.exists("templates/header.ascii"):
            with open("templates/header.ascii", "r", encoding="utf-8") as f:
                header = f.read()
        else:
            header = ""

    if width is None:
        width = get_terminal_width()

    if os.path.exists("templates/resume.ascii"):
        with open("templates/resume.ascii", "r", encoding="utf-8") as f:
            template_str = f.read()
        raw_output = jinja2.Template(template_str).render(
            header=header, resume=resume_data, support=support
        )
        return wrap_ascii_text(raw_output, width=width)

    return get_resume_txt(support=support, resume_data=resume_data, width=width)


def get_resume_source_mtime() -> float:
    """Get the latest modification timestamp of resume templates, data, and styling assets."""
    source_files = [
        "data/resume.json",
        "templates/resume.html",
        "templates/resume.ascii",
        "templates/assets/css/resume-print.css",
        "templates/assets/css/resume-custom.css",
        "templates/assets/css/resume.min.css",
        "templates/assets/css/styles.min.css",
        "templates/assets/bootstrap/css/bootstrap.min.css",
        "templates/assets/img/nathanwoodburn.jpeg",
    ]
    mtimes = [os.path.getmtime(f) for f in source_files if os.path.exists(f)]
    return max(mtimes) if mtimes else 0.0


def build_resume_pdf(support: bool = False, output_path: str | None = None) -> str:
    """
    Build the resume PDF from templates/resume.html and CSS assets using headless Chromium.
    Returns the path to the generated PDF.
    """
    target_pdf = output_path or (
        "data/resume_support.pdf" if support else "data/resume.pdf"
    )
    chromium_bin = find_chromium()
    if not chromium_bin:
        print("Warning: Failed to find chromium binary")
        return target_pdf

    os.makedirs(os.path.dirname(os.path.abspath(target_pdf)), exist_ok=True)

    with open("templates/resume.html", "r", encoding="utf-8") as f:
        html = f.read()

    css_parts = []
    for css_rel in [
        "templates/assets/bootstrap/css/bootstrap.min.css",
        "templates/assets/css/styles.min.css",
        "templates/assets/css/resume.min.css",
        "templates/assets/css/resume-custom.css",
        "templates/assets/css/resume-print.css",
    ]:
        if os.path.exists(css_rel):
            with open(css_rel, "r", encoding="utf-8") as cf:
                css_parts.append(cf.read())

    resume_data = get_resume_data(support=support)
    rendered = jinja2.Template(html).render(
        resume=resume_data,
        support=support,
        asset_url=lambda p: f"/assets/{p.lstrip('/').removeprefix('assets/')}",
    )
    rendered = rendered.replace(
        "</head>",
        f"<style>\n{chr(10).join(css_parts)}\n</style>\n</head>",
    )
    assets_dir = os.path.abspath("templates/assets")
    rendered = rendered.replace("/assets/", f"file://{assets_dir}/")

    tmp_html = f"data/.tmp_resume_{'support' if support else 'main'}.html"
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(rendered)

    try:
        subprocess.run(
            [
                chromium_bin,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--allow-file-access-from-files",
                "--enable-local-file-accesses",
                "--no-pdf-header-footer",
                "--generate-pdf-document-outline",
                f"--print-to-pdf={os.path.abspath(target_pdf)}",
                f"file://{os.path.abspath(tmp_html)}",
            ],
            check=True,
            timeout=30,
            capture_output=True,
        )
    except (subprocess.SubprocessError, OSError) as e:
        print(f"Warning: Failed to build resume PDF via Chromium: {e}")
    finally:
        if os.path.exists(tmp_html):
            try:
                os.remove(tmp_html)
            except OSError:
                pass

    return target_pdf


def get_resume_pdf(support: bool = False, force: bool = False) -> str:
    """
    Get the resume PDF path, automatically rebuilding it if source files were updated.
    """
    target_pdf = "data/resume_support.pdf" if support else "data/resume.pdf"
    needs_build = (
        force
        or not os.path.exists(target_pdf)
        or os.path.getmtime(target_pdf) < get_resume_source_mtime()
    )
    if needs_build:
        build_resume_pdf(support=support, output_path=target_pdf)

    return target_pdf


def generate_sitemap(base_url: str = "https://nathan.woodburn.au") -> str:
    """
    Generate an XML sitemap dynamically covering all static pages,
    blog posts, and now updates.
    """
    base_url = base_url.rstrip("/")
    entries = []

    # Main site routes: (route, priority, changefreq, source_template)
    static_routes = [
        ("/", 1.0, "weekly", "templates/index.html"),
        ("/blog", 0.9, "weekly", "templates/blog/blog.html"),
        ("/now", 0.9, "weekly", "templates/now.html"),
        ("/about", 0.8, "monthly", "templates/about.html"),
        ("/projects", 0.8, "monthly", "templates/projects.html"),
        ("/tools", 0.8, "monthly", "templates/tools.html"),
        ("/resume", 0.8, "monthly", "templates/resume.html"),
        ("/donate", 0.7, "monthly", "templates/donate.html"),
        ("/podcast", 0.7, "monthly", "templates/podcast.html"),
        ("/now/old", 0.5, "monthly", "templates/now/old.html"),
        ("/pgp", 0.5, "yearly", "templates/pgp.html"),
        ("/gitpgp", 0.5, "yearly", "templates/gitpgp.html"),
    ]

    for route, prio, freq, src_file in static_routes:
        lastmod = None
        if os.path.exists(src_file):
            lastmod = datetime.datetime.fromtimestamp(
                os.path.getmtime(src_file), tz=datetime.UTC
            ).strftime("%Y-%m-%d")
        entries.append(
            {
                "loc": base_url + ("" if route == "/" else route),
                "priority": f"{prio:.1f}",
                "changefreq": freq,
                "lastmod": lastmod,
            }
        )

    # Blog posts from data/blog/
    blog_dir = "data/blog"
    if os.path.isdir(blog_dir):
        for f in sorted(os.listdir(blog_dir)):
            if f.endswith(".md"):
                slug = os.path.splitext(f)[0]
                file_path = os.path.join(blog_dir, f)
                lastmod = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path), tz=datetime.UTC
                ).strftime("%Y-%m-%d")
                entries.append(
                    {
                        "loc": f"{base_url}/blog/{slug}",
                        "priority": "0.7",
                        "changefreq": "monthly",
                        "lastmod": lastmod,
                    }
                )

    # Now updates from data/now/
    now_dir = "data/now"
    if os.path.isdir(now_dir):
        for f in sorted(os.listdir(now_dir)):
            if f.endswith(".md"):
                slug = os.path.splitext(f)[0]
                parts = slug.split("_")
                if len(parts) == 3 and all(p.isdigit() for p in parts):
                    year = f"20{parts[0]}" if len(parts[0]) == 2 else parts[0]
                    lastmod = f"{year}-{parts[1]}-{parts[2]}"
                else:
                    file_path = os.path.join(now_dir, f)
                    lastmod = datetime.datetime.fromtimestamp(
                        os.path.getmtime(file_path), tz=datetime.UTC
                    ).strftime("%Y-%m-%d")
                entries.append(
                    {
                        "loc": f"{base_url}/now/{slug}",
                        "priority": "0.6",
                        "changefreq": "yearly",
                        "lastmod": lastmod,
                    }
                )

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for e in entries:
        xml_lines.append("    <url>")
        xml_lines.append(f"        <loc>{e['loc']}</loc>")
        if e.get("lastmod"):
            xml_lines.append(f"        <lastmod>{e['lastmod']}</lastmod>")
        xml_lines.append(f"        <changefreq>{e['changefreq']}</changefreq>")
        xml_lines.append(f"        <priority>{e['priority']}</priority>")
        xml_lines.append("    </url>")
    xml_lines.append("</urlset>\n")

    return "\n".join(xml_lines)


def build_sitemap_file(
    output_path: str = "templates/sitemap.xml",
    base_url: str = "https://nathan.woodburn.au",
) -> str:
    """Generate and write sitemap.xml to file."""
    sitemap_content = generate_sitemap(base_url=base_url)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(sitemap_content)
    return output_path


if __name__ == "__main__":
    import sys

    support = "--support" in sys.argv or "-s" in sys.argv
    if "--json" in sys.argv:
        print(json.dumps(get_resume_data(support=support), indent=2))
    elif "--md" in sys.argv or "--markdown" in sys.argv:
        print(get_resume_md(support=support))
    elif "--txt" in sys.argv or "--text" in sys.argv:
        print(get_resume_txt(support=support))
    elif "--ascii" in sys.argv or "--cli" in sys.argv:
        print(get_resume_ascii(support=support))
    elif "--build-sitemap" in sys.argv or "--sitemap" in sys.argv:
        p = build_sitemap_file()
        print(f"Generated sitemap at {p}")
    elif "--build-resume" in sys.argv or "-b" in sys.argv:
        print("Building standard resume PDF...")
        p1 = build_resume_pdf(support=False)
        print(f"Built {p1} ({os.path.getsize(p1)} bytes)")
        print("Building technical support resume PDF...")
        p2 = build_resume_pdf(support=True)
        print(f"Built {p2} ({os.path.getsize(p2)} bytes)")
        print("Resume PDF build finished.")
    elif len(sys.argv) == 1:
        print("Building standard resume PDF...")
        p1 = build_resume_pdf(support=False)
        print(f"Built {p1} ({os.path.getsize(p1)} bytes)")
        print("Building technical support resume PDF...")
        p2 = build_resume_pdf(support=True)
        print(f"Built {p2} ({os.path.getsize(p2)} bytes)")
        print("Resume PDF build finished.")
        p3 = build_sitemap_file()
        print(f"Built {p3}")
