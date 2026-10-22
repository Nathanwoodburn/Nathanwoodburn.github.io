import argparse
import datetime
import hashlib
import json
import os
from zoneinfo import ZoneInfo

import dotenv
import qrcode
from flask import (
    Flask,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
)
from flask_cors import CORS
from PIL import Image
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L
from werkzeug.middleware.proxy_fix import ProxyFix

dotenv.load_dotenv()

# Import blueprints
from blueprints import acme, api, blog, now, podcast, resume, spotify, wellknown
from cache_helper import (
    get_coin_names,
    get_git_latest_activity,
    get_projects,
    get_wallet_domains,
    get_wallet_tokens,
)
from curl import curl_response, finger_response
from tools import (
    error_response,
    generate_sitemap,
    get_tools_data,
    getAddress,
    getFilePath,
    getHandshakeScript,
    isCLI,
    isFinger,
    render_ascii_terminal,
)

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=1, x_host=1)
CORS(app)


# Register blueprints
for module in [now, blog, wellknown, api, podcast, acme, spotify, resume]:
    app.register_blueprint(module.app)


_asset_version_cache: dict[str, tuple[float, str]] = {}


def get_asset_version(rel_path: str) -> str | None:
    full_path = os.path.join("templates/assets", rel_path)
    try:
        mtime = os.path.getmtime(full_path)
        cached = _asset_version_cache.get(rel_path)
        if cached and cached[0] == mtime:
            return cached[1]
        with open(full_path, "rb") as f:
            v = hashlib.sha256(f.read()).hexdigest()[:10]
        _asset_version_cache[rel_path] = (mtime, v)
        return v
    except OSError:
        return None


def asset_url(path: str) -> str:
    rel_path = path.lstrip("/").removeprefix("assets/").lstrip("/")
    v = get_asset_version(rel_path)
    if v:
        return f"/assets/{rel_path}?v={v}"
    return f"/assets/{rel_path}"


@app.context_processor
def inject_site_context():
    try:
        root = request.url_root.rstrip("/")
        path = request.path.rstrip("/")
        canonical_url = root + "/" if not path else root + path
    except RuntimeError:
        root = "https://nathan.woodburn.au"
        canonical_url = "https://nathan.woodburn.au/"

    return {
        "site_url": root,
        "canonical_url": canonical_url,
        "asset_url": asset_url,
    }


# region Config/Constants

EXCEMPT_ROUTES = ["404", "header", "error", "403", "500"]
RESTRICTED_ROUTES = ["ascii"]
REDIRECT_ROUTES = {
    "contact": "/#contact",
    "meet": "https://cloud.woodburn.au/apps/calendar/appointment/PamrmmspWJZr",
    "meeting": "https://cloud.woodburn.au/apps/calendar/appointment/PamrmmspWJZr",
    "appointment": "https://cloud.woodburn.au/apps/calendar/appointment/PamrmmspWJZr",
    "donate/more": "/donate",
    "index": "/",
    "index.ascii": "/",
    "security.txt": "/.well-known/security.txt",
}
DOWNLOAD_ROUTES = {"pgp": "data/nathanwoodburn.asc"}

SITES = []
if os.path.isfile("data/sites.json"):
    with open("data/sites.json") as file:
        SITES = json.load(file)
        # Remove any sites that are not enabled
        SITES = [site for site in SITES if "enabled" not in site or site["enabled"]]

TZ = ZoneInfo(os.getenv("TIMEZONE", "Australia/Sydney"))

# endregion

# region Assets routes


@app.route("/assets/<path:path>")
def asset(path):
    if os.path.isfile("templates/assets/" + path):
        if path.endswith(".json"):
            return send_from_directory(
                "templates/assets", path, mimetype="application/json"
            )
        return send_from_directory("templates/assets", path)

    # Custom matching for images
    pathMap = {
        "img/hns/w": "img/external/HNS/white",
        "img/hns/b": "img/external/HNS/black",
        "img/hns": "img/external/HNS/black",
    }

    for key, value in pathMap.items():
        if path.startswith(key):
            tmpPath = path.replace(key, value)
            if os.path.isfile("templates/assets/" + tmpPath):
                return send_from_directory("templates/assets", tmpPath)

    # Try looking in other directories first (excluding external), then fallback to external
    filename: str = path.split("/")[-1]
    if filename:
        external_dir = os.path.abspath("templates/assets/img/external")

        # 1. Search in non-external directories
        for root, dirs, files in os.walk("templates/assets"):
            root_abs = os.path.abspath(root)
            if root_abs == external_dir or root_abs.startswith(external_dir + os.sep):
                continue
            if filename in files:
                if filename.endswith(".json"):
                    return send_from_directory(
                        root, filename, mimetype="application/json"
                    )
                return send_from_directory(root, filename)

        # 2. Fallback to external images section if not in any other directory
        if os.path.isdir(external_dir):
            for root, dirs, files in os.walk(external_dir):
                if filename in files:
                    if filename.endswith(".json"):
                        return send_from_directory(
                            root, filename, mimetype="application/json"
                        )
                    return send_from_directory(root, filename)

    return error_response(request)


@app.route("/fonts/<path:path>")
def fonts(path):
    if os.path.isfile("templates/assets/fonts/" + path):
        return send_from_directory("templates/assets/fonts", path)
    return error_response(request)


@app.route("/sitemap")
@app.route("/sitemap.xml")
def sitemap():
    sitemap_xml = generate_sitemap(base_url="https://nathan.woodburn.au")
    return make_response(
        sitemap_xml, 200, {"Content-Type": "application/xml; charset=utf-8"}
    )


@app.route("/robots.txt")
def robots_txt():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /ascii\n"
        "\n"
        "Sitemap: https://nathan.woodburn.au/sitemap.xml\n"
    )
    return make_response(content, 200, {"Content-Type": "text/plain; charset=utf-8"})


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
    response = make_response(send_from_directory("pwa", "sw.js"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.after_request
def add_caching_headers(response):
    if request.path == "/sw.js":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Spotify now playing and dynamic playback endpoints must never be cached
    if request.path.startswith(("/api/v1/playing", "/api/playing", "/spotify")):
        response.headers["Cache-Control"] = (
            "no-cache, no-store, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Static assets: versioned assets can be cached aggressively (1 year, immutable);
    # unversioned assets must be revalidated so changes on disk are picked up immediately.
    if request.path.startswith("/assets/"):
        if request.args.get("v"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "public, no-cache, must-revalidate"
            response.headers.pop("Expires", None)
        return response

    if response.mimetype == "text/html" and response.status_code == 200:
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.add_etag()
        return response.make_conditional(request)

    return response


# endregion


# region Misc routes
@app.route("/actions.json")
def sol_actions():
    return jsonify(
        {"rules": [{"pathPattern": "/donate**", "apiPath": "/api/v1/donate**"}]}
    )


@app.route("/api/<path:function>")
def api_legacy(function):
    # Check if function is in api blueprint
    for rule in app.url_map.iter_rules():
        # Check if the redirect route exists
        if rule.rule == f"/api/v1/{function}":
            return redirect(f"/api/v1/{function}", code=301)
    return error_response(request, message="404 Not Found", code=404)


# endregion

# region Main routes


@app.route("/")
def index():
    # Check if host if podcast.woodburn.au
    if "podcast.woodburn.au" in request.host:
        return render_template("podcast.html")

    if isCLI(request):
        return curl_response(request)

    if isFinger(request):
        return finger_response(request)

    # Use cached git data
    git = get_git_latest_activity()
    repo_name = git["repo"]["name"].lower()
    repo_description = git["repo"]["description"]

    # Use cached projects data
    projects = get_projects(limit=8)

    # Special names
    if repo_name == "nathanwoodburn.github.io":
        repo_name = "Nathan.Woodburn/"

    html_url = git["repo"]["html_url"]
    repo = '<a href="' + html_url + '" target="_blank">' + repo_name + "</a>"

    server_now = datetime.datetime.now().astimezone()
    timezone_offset = TZ.utcoffset(server_now).total_seconds() / 3600  # type: ignore
    time = server_now.strftime("%B %d")
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
    time += f"startClock({timezone_offset});"
    time += "</script>"

    HNSaddress = getAddress("HNS")
    SOLaddress = getAddress("SOL")
    BTCaddress = getAddress("BTC")
    ETHaddress = getAddress("ETH")
    return render_template(
        "index.html",
        handshake_scripts=getHandshakeScript(request.host),
        HNS=HNSaddress,
        SOL=SOLaddress,
        BTC=BTCaddress,
        ETH=ETHaddress,
        repo=repo,
        repo_description=repo_description,
        sites=SITES,
        projects=projects,
        time=time,
        message="",
    )


# region Donate


@app.route("/donate")
def donate():
    if isCLI(request):
        return curl_response(request)

    coinList = os.listdir(".well-known/wallets")
    coinList = [file for file in coinList if file[0] != "."]
    coinList.sort()

    tokenList = get_wallet_tokens()
    coinNames = get_coin_names()

    coins = ""
    default_coins = ["btc", "eth", "hns", "sol", "xrp", "ada", "dot"]

    for file in coinList:
        coin_name = coinNames.get(file, file)
        display_style = "" if file.lower() in default_coins else "display:none;"
        coins += f'<a class="dropdown-item" style="{display_style}" href="?c={file.lower()}">{coin_name}</a>'

    for token in tokenList:
        chain_display = f" on {token['chain']}" if token["chain"] != "null" else ""
        symbol_display = (
            f" ({token['symbol']}{chain_display})"
            if token["symbol"] != token["name"]
            else chain_display
        )
        coins += f'<a class="dropdown-item" style="display:none;" href="?t={token["symbol"].lower()}&c={token["chain"].lower()}">{token["name"]}{symbol_display}</a>'

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
    cryptoHTML = ""

    proof = ""
    if os.path.isfile(f".well-known/wallets/.{crypto}.proof"):
        proof = f'<a href="/.well-known/wallets/.{crypto}.proof" target="_blank"><img src="/assets/img/proof.png" alt="Proof of ownership" style="width: 100%; max-width: 30px; margin-left: 10px;"></a>'

    if os.path.isfile(f".well-known/wallets/{crypto}"):
        with open(f".well-known/wallets/{crypto}") as file:
            address = file.read()
            coin_display = coinNames.get(crypto, crypto)
            if not token:
                cryptoHTML += f"<br>Donate with {coin_display}:"
            else:
                token_symbol = (
                    f" ({token['symbol']})" if token["symbol"] != token["name"] else ""
                )
                cryptoHTML += (
                    f"<br>Donate with {token['name']}{token_symbol} on {crypto}:"
                )
            cryptoHTML += f'<br><code data-bs-toggle="tooltip" data-bss-tooltip="" id="crypto-address" class="address" style="color: rgb(242,90,5);display: inline-block;" data-bs-original-title="Click to copy">{address}</code>'

            if proof:
                cryptoHTML += proof
    elif token:
        if "address" in token:
            address = token["address"]
            token_symbol = (
                f" ({token['symbol']})" if token["symbol"] != token["name"] else ""
            )
            chain_display = f" on {crypto}" if crypto != "NULL" else ""
            cryptoHTML += (
                f"<br>Donate with {token['name']}{token_symbol}{chain_display}:"
            )
            cryptoHTML += f'<br><code data-bs-toggle="tooltip" data-bss-tooltip="" id="crypto-address" class="address" style="color: rgb(242,90,5);display: inline-block;" data-bs-original-title="Click to copy">{address}</code>'
            if proof:
                cryptoHTML += proof
        else:
            cryptoHTML += f"<br>Invalid offchain token: {token['symbol']}<br>"
    else:
        cryptoHTML += f"<br>Invalid chain: {crypto}<br>"

    domains = get_wallet_domains()
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
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(data)
    qr.make()

    qr_image: Image.Image = qr.make_image(
        fill_color="black", back_color="white"
    ).convert("RGB")  # type: ignore

    # Add logo
    logo = Image.open("templates/assets/img/favicon/logo.png")
    basewidth = qr_image.size[0] // 3
    wpercent = basewidth / float(logo.size[0])
    hsize = int(float(logo.size[1]) * float(wpercent))
    logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)
    pos = (
        (qr_image.size[0] - logo.size[0]) // 2,
        (qr_image.size[1] - logo.size[1]) // 2,
    )
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

    if isCLI(request) or request.args.get("raw") == "1":
        return ascii_art, 200, {"Content-Type": "text/plain; charset=utf-8"}
    return render_ascii_terminal(
        ascii_art,
        title="ASCII Art - Terminal",
        filename="ascii.txt",
        web_link="/",
    )


@app.route("/tools")
def tools():
    if isCLI(request):
        return curl_response(request)
    return render_template("tools.html", tools=get_tools_data())


# endregion
# region Error Catching


# Catch all for GET requests
@app.route("/<path:path>")
def catch_all(path: str):
    if path.lower().endswith(".html"):
        return redirect(path.lower().removesuffix(".html"), code=302)

    if path.lower() in RESTRICTED_ROUTES:
        return error_response(request, message="Restricted route", code=403)

    if path.lower() in EXCEMPT_ROUTES:
        return error_response(request)

    # If curl request, return curl response
    if isCLI(request):
        return curl_response(request)

    if path in REDIRECT_ROUTES:
        return redirect(REDIRECT_ROUTES[path], code=302)

    # If an ascii file is requested directly in a browser
    if path.endswith(".ascii"):
        resp = curl_response(request)
        if isinstance(resp, tuple) and len(resp) >= 1:
            raw_text = resp[0]
            if isCLI(request) or request.args.get("raw") == "1":
                return resp
            stem = path.removesuffix(".ascii")
            return render_ascii_terminal(
                raw_text,
                title=f"{path} - Terminal",
                filename=path,
                web_link=f"/{stem}" if stem != "index" else "/",
            )

    # If file exists, load it
    if os.path.isfile("templates/" + path):
        return render_template(
            path, handshake_scripts=getHandshakeScript(request.host), sites=SITES
        )

    # Try with .html
    if os.path.isfile("templates/" + path + ".html"):
        return render_template(
            path + ".html",
            handshake_scripts=getHandshakeScript(request.host),
            sites=SITES,
        )

    if os.path.isfile("templates/" + path.strip("/") + ".html"):
        return render_template(
            path.strip("/") + ".html",
            handshake_scripts=getHandshakeScript(request.host),
            sites=SITES,
        )

    # Try to find a file matching
    if path.count("/") < 1:
        # Try to find a file matching
        filename = getFilePath(path, "templates")
        if filename:
            return send_file(filename)

    return error_response(request)


@app.errorhandler(403)
def forbidden(e):
    return error_response(request, message="Forbidden", code=403)


@app.errorhandler(404)
def not_found(e):
    return error_response(request)


@app.errorhandler(500)
def server_error(e):
    return error_response(request, message="Internal Server Error", code=500)


@app.route("/test")
def test_route_broken():
    return


# endregion


if __name__ == "__main__":
    # If --host argument is passed, use that as host, otherwise use 127.0.0.1
    parser = argparse.ArgumentParser(description="Run the Flask server.")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default="5000")
    args = parser.parse_args()

    app.run(debug=True, port=args.port, host=args.host)
