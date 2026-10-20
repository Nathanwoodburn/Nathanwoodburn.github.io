from flask import Blueprint, jsonify, render_template, request, send_file

from curl import curl_response, get_header
from tools import (
    get_resume_data,
    get_resume_md,
    get_resume_pdf,
    get_resume_txt,
    get_terminal_width,
    isCLI,
    parse_support_arg,
    wrap_ascii_text,
)

app = Blueprint("resume", __name__)


@app.route("/resume")
def resume():
    if isCLI(request):
        return curl_response(request)
    support = parse_support_arg(request)
    resume_data = get_resume_data(support=support)
    return render_template("resume.html", resume=resume_data, support=support)


@app.route("/resume.json")
def resume_json():
    support = parse_support_arg(request)
    resume_data = get_resume_data(support=support)
    return jsonify(
        {
            "name": resume_data["name"],
            "profile_image": resume_data["profile_image"],
            "summary": resume_data["active_summary"],
            "title": resume_data["active_title"],
            "contact": resume_data["contact"],
            "education": resume_data["education"],
            "experience": resume_data["experience"],
            "projects": resume_data["projects"],
            "skills": resume_data["skills"],
        }
    )


@app.route("/resume.md")
def resume_md():
    support = parse_support_arg(request)
    md_content = get_resume_md(support=support)
    return md_content, 200, {"Content-Type": "text/markdown; charset=utf-8"}


@app.route("/resume.txt")
def resume_txt():
    support = parse_support_arg(request)
    width = get_terminal_width(request)
    txt_content = get_resume_txt(support=support, width=width)
    return txt_content, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/resume.ascii")
def resume_ascii():
    support = parse_support_arg(request)
    resume_data = get_resume_data(support=support)
    width = get_terminal_width(request)
    output = render_template(
        "resume.ascii",
        header=get_header(),
        resume=resume_data,
        support=support,
    )
    return (
        wrap_ascii_text(output, width=width),
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


@app.route("/resume.pdf")
def resume_pdf():
    support = parse_support_arg(request)
    force = bool(request.args.get("force") or request.args.get("rebuild"))
    pdf_path = get_resume_pdf(support=support, force=force)
    return send_file(pdf_path, mimetype="application/pdf")
