#!/usr/bin/env python3
import json
import os
import shutil
import subprocess

import jinja2


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


def build_all_resumes():
    print("Building standard resume PDF...")
    p1 = build_resume_pdf(support=False)
    if os.path.exists(p1):
        print(f"Built {p1} ({os.path.getsize(p1)} bytes)")
    print("Building technical support resume PDF...")
    p2 = build_resume_pdf(support=True)
    if os.path.exists(p2):
        print(f"Built {p2} ({os.path.getsize(p2)} bytes)")
    print("Resume PDF build finished.")


if __name__ == "__main__":
    build_all_resumes()
