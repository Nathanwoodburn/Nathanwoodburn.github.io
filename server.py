import json
from flask import (
    Flask,
    make_response,
    redirect,
    request,
    jsonify,
    render_template,
    send_from_directory,
    send_file,
)
from flask_cors import CORS
import os
import dotenv
import requests
import datetime
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_H
from ansi2html import Ansi2HTMLConverter
from PIL import Image
# Import blueprints
from blueprints.now import now_bp
from blueprints.blog import blog_bp
from blueprints.wellknown import wk_bp
from blueprints.api import api_bp
from blueprints.podcast import podcast_bp
from blueprints.acme import acme_bp
from tools import isCurl, isCrawler, getAddress, getFilePath, error_response, getClientIP, json_response, getHandshakeScript, get_tools_data
from curl import curl_response

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(now_bp, url_prefix='/now')
app.register_blueprint(blog_bp, url_prefix='/blog')
app.register_blueprint(wk_bp, url_prefix='/.well-known')
app.register_blueprint(api_bp, url_prefix='/api/v1')
app.register_blueprint(podcast_bp)
app.register_blueprint(acme_bp)

dotenv.load_dotenv()

# region Config/Constants

# Rate limiting for hosting enquiries
EMAIL_REQUEST_COUNT = {}  # Track requests by email
IP_REQUEST_COUNT = {}     # Track requests by IP
EMAIL_RATE_LIMIT = 3      # Max 3 requests per email per hour
IP_RATE_LIMIT = 5         # Max 5 requests per IP per hour
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds

RESTRICTED_ROUTES = ["ascii"]
REDIRECT_ROUTES = {
    "contact": "/#contact"
}
DOWNLOAD_ROUTES = {
    "pgp": "data/nathanwoodburn.asc"
}

SITES = []
if os.path.isfile("data/sites.json"):
    with open("data/sites.json") as file:
        SITES = json.load(file)
        # Remove any sites that are not enabled
        SITES = [
            site for site in SITES if "enabled" not in site or site["enabled"]
        ]

PROJECTS = []
PROJECTS_UPDATED = 0

NC_CONFIG = requests.get(
    "https://cloud.woodburn.au/s/4ToXgFe3TnnFcN7/download/website-conf.json"
).json()

# endregion

# region Assets routes


@app.route("/assets/<path:path>")
def asset(path):
    if path.endswith(".json"):
        return send_from_directory(
            "templates/assets", path, mimetype="application/json"
        )

    if os.path.isfile("templates/assets/" + path):
        return send_from_directory("templates/assets", path)

    # Custom matching for images
    pathMap = {
        "img/hns/w": "img/external/HNS/white",
        "img/hns/b": "img/external/HNS/black",
        "img/hns": "img/external/HNS/black",
    }

    for key in pathMap:
        if path.startswith(key):
            tmpPath = path.replace(key, pathMap[key])
            if os.path.isfile("templates/assets/" + tmpPath):
                return send_from_directory("templates/assets", tmpPath)

    # Try looking in one of the directories
    filename: str = path.split("/")[-1]
    if (
        filename.endswith(".png")
        or filename.endswith(".jpg")
        or filename.endswith(".jpeg")
        or filename.endswith(".svg")
    ):
        if os.path.isfile("templates/assets/img/" + filename):
            return send_from_directory("templates/assets/img", filename)
        if os.path.isfile("templates/assets/img/favicon/" + filename):
            return send_from_directory("templates/assets/img/favicon", filename)

    return error_response(request)


@app.route("/sitemap")
@app.route("/sitemap.xml")
def sitemap():
    # Remove all .html from sitemap
    if not os.path.isfile("templates/sitemap.xml"):
        return error_response(request)
    with open("templates/sitemap.xml") as file:
        sitemap = file.read()

    sitemap = sitemap.replace(".html", "")
    return make_response(sitemap, 200, {"Content-Type": "application/xml"})


@app.route("/favicon.<ext>")
def favicon(ext):
    if ext not in ("png", "svg", "ico"):
        return error_response(request)
    return send_from_directory("templates/assets/img/favicon", f"favicon.{ext}")


@app.route("/<name>.js")
def javascript(name):
    # Check if file in js directory
    if not os.path.isfile("templates/assets/js/" + request.path.split("/")[-1]):
        return error_response(request)
    return send_from_directory("templates/assets/js", request.path.split("/")[-1])


@app.route("/download/<path:path>")
def download(path):
    if path not in DOWNLOAD_ROUTES:
        return error_response(request, message="Invalid download")
    # Check if file exists
    path = DOWNLOAD_ROUTES[path]
    if os.path.isfile(path):
        return send_file(path)

    return error_response(request, message="File not found")

# endregion
# region PWA routes


@app.route("/manifest.json")
def manifest():
    host = request.host

    # Read as json
    with open("pwa/manifest.json") as file:
        manifest = json.load(file)
    url = f"https://{host}"
    if host == "localhost:5000" or host == "127.0.0.1:5000":
        url = "http://127.0.0.1:5000"

    manifest["start_url"] = url
    manifest["scope"] = url
    return jsonify(manifest)


@app.route("/sw.js")
def serviceWorker():
    return send_from_directory("pwa", "sw.js")

# endregion


# region Misc routes


@app.route("/meet")
@app.route("/meeting")
@app.route("/appointment")
def meetingLink():
    return redirect(
        "https://cloud.woodburn.au/apps/calendar/appointment/PamrmmspWJZr", code=302
    )


@app.route("/links")
def links():
    return render_template("link.html")


@app.route("/api/<path:function>")
def api_legacy(function):
    # Check if function is in api blueprint
    for rule in app.url_map.iter_rules():
        # Check if the redirect route exists
        if rule.rule == f"/api/v1/{function}":
            return redirect(f"/api/v1/{function}", code=301)
    return error_response(request, message="404 Not Found", code=404)


@app.route("/actions.json")
def sol_actions():
    return jsonify(
        {"rules": [{"pathPattern": "/donate**", "apiPath": "/api/v1/donate**"}]}
    )

# endregion

# region Main routes


@app.route("/")
def index():
    global PROJECTS
    global PROJECTS_UPDATED

    # Check if host if podcast.woodburn.au
    if "podcast.woodburn.au" in request.host:
        return render_template("podcast.html")

    loaded = False
    if request.referrer:
        # Check if referrer includes nathan.woodburn.au
        if "nathan.woodburn.au" in request.referrer:
            loaded = True
    if request.cookies.get("loaded"):
        loaded = True

    # Always load if load is in the query string
    if request.args.get("load"):
        loaded = False
    if isCurl(request):
        return curl_response(request)

    if not loaded and not isCrawler(request):
        # Set cookie
        resp = make_response(
            render_template("loading.html").replace(
                "https://nathan.woodburn.au/loading", "https://nathan.woodburn.au/"
            ),
            200,
            {"Content-Type": "text/html"},
        )
        resp.set_cookie("loaded", "true", max_age=604800)
        return resp

    try:
        git = requests.get(
            "https://git.woodburn.au/api/v1/users/nathanwoodburn/activities/feeds?only-performed-by=true&limit=1",
            headers={"Authorization": os.getenv("GIT_AUTH") if os.getenv("GIT_AUTH") else os.getenv("git_token")},
        )
        git = git.json()
        git = git[0]
        repo_name = git["repo"]["name"]
        repo_name = repo_name.lower()
        repo_description = git["repo"]["description"]
    except Exception as e:
        repo_name = "nathanwoodburn.github.io"
        repo_description = "Personal website"
        git = {
            "repo": {
                "html_url": "https://nathan.woodburn.au",
                "name": "nathanwoodburn.github.io",
                "description": "Personal website",
            }
        }
        print(f"Error getting git data: {e}")

    # Get only repo names for the newest updates
    if PROJECTS == [] or PROJECTS_UPDATED < (datetime.datetime.now() - datetime.timedelta(
        hours=2
    )).timestamp():
        projectsreq = requests.get(
            "https://git.woodburn.au/api/v1/users/nathanwoodburn/repos"
        )

        PROJECTS = projectsreq.json()

        # Check for next page
        pageNum = 1
        while 'rel="next"' in projectsreq.headers["link"]:
            projectsreq = requests.get(
                "https://git.woodburn.au/api/v1/users/nathanwoodburn/repos?page="
                + str(pageNum)
            )
            PROJECTS += projectsreq.json()
            pageNum += 1

        for project in PROJECTS:
            if (
                project["avatar_url"] == "https://git.woodburn.au/"
                or project["avatar_url"] == ""
            ):
                project["avatar_url"] = "/favicon.png"
            project["name"] = project["name"].replace(
                "_", " ").replace("-", " ")
        # Sort by last updated
        projectsList = sorted(
            PROJECTS, key=lambda x: x["updated_at"], reverse=True)
        PROJECTS = []
        projectNames = []
        projectNum = 0
        while len(PROJECTS) < 3:
            if projectsList[projectNum]["name"] not in projectNames:
                PROJECTS.append(projectsList[projectNum])
                projectNames.append(projectsList[projectNum]["name"])
            projectNum += 1
        PROJECTS_UPDATED = datetime.datetime.now().timestamp()

    custom = ""
    # Check for downtime
    uptime = requests.get(
        "https://uptime.woodburn.au/api/status-page/main/badge")
    uptime = uptime.content.count(b"Up") > 1

    if uptime:
        custom += "<style>#downtime{display:none !important;}</style>"
    else:
        custom += "<style>#downtime{opacity:1;}</style>"
    # Special names
    if repo_name == "nathanwoodburn.github.io":
        repo_name = "Nathan.Woodburn/"

    html_url = git["repo"]["html_url"]
    repo = '<a href="' + html_url + '" target="_blank">' + repo_name + "</a>"        

    # Get time
    timezone_offset = datetime.timedelta(hours=NC_CONFIG["time-zone"])
    timezone = datetime.timezone(offset=timezone_offset)
    time = datetime.datetime.now(tz=timezone)

    time = time.strftime("%B %d")
    time += """
    <span id=\"time\"></span>
    <script>
    function startClock(timezoneOffset) {
    function updateClock() {
        const now = new Date();
        const localTime = new Date(now.getTime() + timezoneOffset * 3600 * 1000);
        const tzName = timezoneOffset >= 0 ? `UTC+${timezoneOffset}` : `UTC`;
        const hours = String(localTime.getUTCHours()).padStart(2, '0');
        const minutes = String(localTime.getUTCMinutes()).padStart(2, '0');
        const seconds = String(localTime.getUTCSeconds()).padStart(2, '0');
        const timeString = `${hours}:${minutes}:${seconds} ${tzName}`;
        document.getElementById('time').textContent = timeString;
    }
    updateClock();
    setInterval(updateClock, 1000);
}
"""
    time += f"startClock({NC_CONFIG['time-zone']});"
    time += "</script>"

    HNSaddress = getAddress("HNS")
    SOLaddress = getAddress("SOL")
    BTCaddress = getAddress("BTC")
    ETHaddress = getAddress("ETH")
    # Set cookie
    resp = make_response(
        render_template(
            "index.html",
            handshake_scripts=getHandshakeScript(request.host),
            HNS=HNSaddress,
            SOL=SOLaddress,
            BTC=BTCaddress,
            ETH=ETHaddress,
            repo=repo,
            repo_description=repo_description,
            custom=custom,
            sites=SITES,
            projects=PROJECTS,
            time=time,
            message=NC_CONFIG.get("message",""),
        ),
        200,
        {"Content-Type": "text/html"},
    )
    resp.set_cookie("loaded", "true", max_age=604800)

    return resp

# region Donate
@app.route("/donate")
def donate():
    if isCurl(request):
        return curl_response(request)

    coinList = os.listdir(".well-known/wallets")
    coinList = [file for file in coinList if file[0] != "."]
    coinList.sort()

    tokenList = []

    with open(".well-known/wallets/.tokens") as file:
        tokenList = file.read()
        tokenList = json.loads(tokenList)

    coinNames = {}
    with open(".well-known/wallets/.coins") as file:
        coinNames = file.read()
        coinNames = json.loads(coinNames)

    coins = ""
    default_coins = ["btc", "eth", "hns", "sol", "xrp", "ada", "dot"]

    for file in coinList:
        if file in coinNames:
            coins += f'<a class="dropdown-item" style="{"display:none;" if file.lower() not in default_coins else ""}" href="?c={file.lower()}">{coinNames[file]}</a>'
        else:
            coins += f'<a class="dropdown-item" style="{"display:none;" if file.lower() not in default_coins else ""}" href="?c={file.lower()}">{file}</a>'

    for token in tokenList:
        if token["chain"] != "null":
            coins += f'<a class="dropdown-item" style="display:none;" href="?t={token["symbol"].lower()}&c={token["chain"].lower()}">{token["name"]} ({token["symbol"] + " on " if token["symbol"] != token["name"] else ""}{token["chain"]})</a>'
        else:
            coins += f'<a class="dropdown-item" style="display:none;" href="?t={token["symbol"].lower()}&c={token["chain"].lower()}">{token["name"]} ({token["symbol"] if token["symbol"] != token["name"] else ""})</a>'

    crypto = request.args.get("c")
    if not crypto:
        instructions = (
            "<br>Donate with cryptocurrency:<br>Select a coin from the dropdown above."
        )
        return render_template(
            "donate.html",
            handshake_scripts=getHandshakeScript(request.host),
            coins=coins,
            default_coins=default_coins,
            crypto=instructions,
        )
    crypto = crypto.upper()

    token = request.args.get("t")
    if token:
        token = token.upper()
        for t in tokenList:
            if t["symbol"].upper() == token and t["chain"].upper() == crypto:
                token = t
                break
        if not isinstance(token, dict):
            token = {"name": "Unknown token", "symbol": token, "chain": crypto}

    address = ""
    domain = ""
    cryptoHTML = ""

    proof = ""
    if os.path.isfile(f".well-known/wallets/.{crypto}.proof"):
        proof = f'<a href="/.well-known/wallets/.{crypto}.proof" target="_blank"><img src="/assets/img/proof.png" alt="Proof of ownership" style="width: 100%; max-width: 30px; margin-left: 10px;"></a>'

    if os.path.isfile(f".well-known/wallets/{crypto}"):
        with open(f".well-known/wallets/{crypto}") as file:
            address = file.read()
            if not token:
                cryptoHTML += f"<br>Donate with {coinNames[crypto] if crypto in coinNames else crypto}:"
            else:
                cryptoHTML += f'<br>Donate with {token["name"]} {"("+token["symbol"]+") " if token["symbol"] != token["name"] else ""}on {crypto}:'
            cryptoHTML += f'<br><code data-bs-toggle="tooltip" data-bss-tooltip="" id="crypto-address" class="address" style="color: rgb(242,90,5);display: inline-block;" data-bs-original-title="Click to copy">{address}</code>'

            if proof:
                cryptoHTML += proof
    elif token:
        if "address" in token:
            address = token["address"]
            cryptoHTML += f'<br>Donate with {token["name"]} {"("+token["symbol"]+")" if token["symbol"] != token["name"] else ""}{" on "+crypto if crypto != "NULL" else ""}:'
            cryptoHTML += f'<br><code data-bs-toggle="tooltip" data-bss-tooltip="" id="crypto-address" class="address" style="color: rgb(242,90,5);display: inline-block;" data-bs-original-title="Click to copy">{address}</code>'
            if proof:
                cryptoHTML += proof
        else:
            cryptoHTML += f'<br>Invalid offchain token: {token["symbol"]}<br>'
    else:
        cryptoHTML += f"<br>Invalid chain: {crypto}<br>"

    if os.path.isfile(".well-known/wallets/.domains"):
        # Get json of all domains
        with open(".well-known/wallets/.domains") as file:
            domains = file.read()
            domains = json.loads(domains)

        if crypto in domains:
            domain = domains[crypto]
            cryptoHTML += "<br>Or send to this domain on compatible wallets:<br>"
            cryptoHTML += f'<code data-bs-toggle="tooltip" data-bss-tooltip="" id="crypto-domain" class="address" style="color: rgb(242,90,5);display: block;" data-bs-original-title="Click to copy">{domain}</code>'
    if address:
        cryptoHTML += (
            '<br><img src="/address/'
            + address
            + '" alt="QR Code" style="width: 100%; max-width: 200px; margin: 20px auto;">'
        )

    copyScript = '<script>document.getElementById("crypto-address").addEventListener("click", function() {navigator.clipboard.writeText(this.innerText);this.setAttribute("data-bs-original-title", "Copied!");const tooltips = document.querySelectorAll(".tooltip-inner");tooltips.forEach(tooltip => {tooltip.innerText = "Copied!";});});document.getElementById("crypto-domain").addEventListener("click", function() {navigator.clipboard.writeText(this.innerText);this.setAttribute("data-bs-original-title", "Copied!");const tooltips = document.querySelectorAll(".tooltip-inner");tooltips.forEach(tooltip => {tooltip.innerText = "Copied!";});});</script>'
    cryptoHTML += copyScript

    return render_template(
        "donate.html",
        handshake_scripts=getHandshakeScript(request.host),
        crypto=cryptoHTML,
        coins=coins,
        default_coins=default_coins,
    )


@app.route("/address/<path:address>")
def qraddress(address):
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(address)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="#110033", back_color="white")

    # Save the QR code image to a temporary file
    qr_image_path = "/tmp/qr_code.png"
    qr_image.save(qr_image_path)  # type: ignore

    # Return the QR code image as a response
    return send_file(qr_image_path, mimetype="image/png")


@app.route("/qrcode/<path:data>")
@app.route("/qr/<path:data>")
def qrcodee(data):
    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(data)
    qr.make()

    qr_image: Image.Image = qr.make_image(
        fill_color="black", back_color="white").convert('RGB')  # type: ignore

    # Add logo
    logo = Image.open("templates/assets/img/favicon/logo.png")
    basewidth = qr_image.size[0]//3
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)
    pos = ((qr_image.size[0] - logo.size[0]) // 2,
           (qr_image.size[1] - logo.size[1]) // 2)
    qr_image.paste(logo, pos, mask=logo)

    qr_image.save("/tmp/qr_code.png")
    return send_file("/tmp/qr_code.png", mimetype="image/png")

# endregion

@app.route("/supersecretpath")
def supersecretpath():
    ascii_art = ""
    if os.path.isfile("data/ascii.txt"):
        with open("data/ascii.txt") as file:
            ascii_art = file.read()

    converter = Ansi2HTMLConverter()
    ascii_art_html = converter.convert(ascii_art)
    return render_template("ascii.html", ascii_art=ascii_art_html)


@app.route("/hosting/send-enquiry", methods=["POST"])
def hosting_post():
    global EMAIL_REQUEST_COUNT
    global IP_REQUEST_COUNT

    if not request.is_json or not request.json:
        return json_response(request, "No JSON data provided", 415)

    # Keys
    # email, cpus, memory, disk, backups, message
    required_keys = ["email", "cpus", "memory", "disk", "backups", "message"]
    for key in required_keys:
        if key not in request.json:
            return json_response(request, f"Missing key: {key}", 400)

    email = request.json["email"]
    ip = getClientIP(request)
    print(f"Hosting enquiry from {email} ({ip})")

    # Check rate limits
    current_time = datetime.datetime.now().timestamp()

    # Check email rate limit
    if email in EMAIL_REQUEST_COUNT:
        if (current_time - EMAIL_REQUEST_COUNT[email]["last_reset"]) > RATE_LIMIT_WINDOW:
            # Reset counter if the time window has passed
            EMAIL_REQUEST_COUNT[email] = {
                "count": 1, "last_reset": current_time}
        else:
            # Increment counter
            EMAIL_REQUEST_COUNT[email]["count"] += 1
            if EMAIL_REQUEST_COUNT[email]["count"] > EMAIL_RATE_LIMIT:
                return json_response(request, "Rate limit exceeded. Please try again later.", 429)
    else:
        # First request for this email
        EMAIL_REQUEST_COUNT[email] = {"count": 1, "last_reset": current_time}

    # Check IP rate limit
    if ip in IP_REQUEST_COUNT:
        if (current_time - IP_REQUEST_COUNT[ip]["last_reset"]) > RATE_LIMIT_WINDOW:
            # Reset counter if the time window has passed
            IP_REQUEST_COUNT[ip] = {"count": 1, "last_reset": current_time}
        else:
            # Increment counter
            IP_REQUEST_COUNT[ip]["count"] += 1
            if IP_REQUEST_COUNT[ip]["count"] > IP_RATE_LIMIT:
                return json_response(request, "Rate limit exceeded. Please try again later.", 429)
    else:
        # First request for this IP
        IP_REQUEST_COUNT[ip] = {"count": 1, "last_reset": current_time}

    cpus = request.json["cpus"]
    memory = request.json["memory"]
    disk = request.json["disk"]
    backups = request.json["backups"]
    message = request.json["message"]

    # Try to convert to correct types
    try:
        cpus = int(cpus)
        memory = float(memory)
        disk = int(disk)
        backups = backups in [True, "true", "True", 1, "1", "yes", "Yes"]
        message = str(message)
        email = str(email)
    except ValueError:
        return json_response(request, "Invalid data types", 400)

    # Basic validation
    if not isinstance(cpus, int) or cpus < 1 or cpus > 64:
        return json_response(request, "Invalid CPUs", 400)
    if not isinstance(memory, float) or memory < 0.5 or memory > 512:
        return json_response(request, "Invalid memory", 400)
    if not isinstance(disk, int) or disk < 10 or disk > 500:
        return json_response(request, "Invalid disk", 400)
    if not isinstance(backups, bool):
        return json_response(request, "Invalid backups", 400)
    if not isinstance(message, str) or len(message) > 1000:
        return json_response(request, "Invalid message", 400)
    if not isinstance(email, str) or len(email) > 100 or "@" not in email:
        return json_response(request, "Invalid email", 400)

    # Send to Discord webhook
    webhook_url = os.getenv("HOSTING_WEBHOOK")
    if not webhook_url:
        return json_response(request, "Hosting webhook not set", 500)

    data = {
        "content": "",
        "embeds": [
            {
                "title": "Hosting Enquiry",
                "description": f"Email: {email}\nCPUs: {cpus}\nMemory: {memory}GB\nDisk: {disk}GB\nBackups: {backups}\nMessage: {message}",
                "color": 16711680,  # Red color
            }
        ],
    }
    headers = {
        "Content-Type": "application/json",
    }
    response = requests.post(webhook_url, json=data, headers=headers)
    if response.status_code != 204 and response.status_code != 200:
        return json_response(request, "Failed to send enquiry", 500)
    return json_response(request, "Enquiry sent", 200)


@app.route("/resume.pdf")
def resume_pdf():
    # Check if file exists
    if os.path.isfile("data/resume.pdf"):
        return send_file("data/resume.pdf")
    return error_response(request, message="Resume not found")

@app.route("/tools")
def tools():
    if isCurl(request):
        return curl_response(request)
    return render_template("tools.html", tools=get_tools_data())

# endregion
# region Error Catching

# Catch all for GET requests


@app.route("/<path:path>")
def catch_all(path: str):
    
    if path.lower().replace(".html", "") in RESTRICTED_ROUTES:
        return error_response(request, message="Restricted route", code=403)

    # If curl request, return curl response
    if isCurl(request):
        return curl_response(request)

    if path in REDIRECT_ROUTES:
        return redirect(REDIRECT_ROUTES[path], code=302)

    # If file exists, load it
    if os.path.isfile("templates/" + path):
        return render_template(path, handshake_scripts=getHandshakeScript(request.host), sites=SITES)

    # Try with .html
    if os.path.isfile("templates/" + path + ".html"):
        return render_template(
            path + ".html", handshake_scripts=getHandshakeScript(request.host), sites=SITES
        )

    if os.path.isfile("templates/" + path.strip("/") + ".html"):
        return render_template(
            path.strip("/") + ".html", handshake_scripts=getHandshakeScript(request.host), sites=SITES
        )

    # Try to find a file matching
    if path.count("/") < 1:
        # Try to find a file matching
        filename = getFilePath(path, "templates")
        if filename:
            return send_file(filename)

    return error_response(request)


@app.errorhandler(404)
def not_found(e):
    return error_response(request)

# endregion


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="127.0.0.1")
