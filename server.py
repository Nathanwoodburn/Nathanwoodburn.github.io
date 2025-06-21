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
from cloudflare import Cloudflare
import datetime
import qrcode
import re
import binascii
import base64
from ansi2html import Ansi2HTMLConverter
from functools import cache
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solders.hash import Hash
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.null_signer import NullSigner
from PIL import Image
from mail import sendEmail
import now
import blog

app = Flask(__name__)
CORS(app)

dotenv.load_dotenv()

handshake_scripts = '<script src="https://nathan.woodburn/handshake.js" domain="nathan.woodburn" async></script><script src="https://nathan.woodburn/https.js" async></script>'

restricted = ["ascii"]
redirects = {
    "contact":"/#contact"
}
downloads = {
    "pgp": "data/nathanwoodburn.asc"
}


sites = []
if os.path.isfile("data/sites.json"):
    with open("data/sites.json") as file:
        sites = json.load(file)
        # Remove any sites that are not enabled
        sites = [
            site for site in sites if "enabled" not in site or site["enabled"] == True
        ]

projects = []
projectsUpdated = 0


ncConfig = requests.get(
    "https://cloud.woodburn.au/s/4ToXgFe3TnnFcN7/download/website-conf.json"
)
ncConfig = ncConfig.json()


@cache
def getAddress(coin: str) -> str:
    address = ""
    if os.path.isfile(".well-known/wallets/" + coin.upper()):
        with open(".well-known/wallets/" + coin.upper()) as file:
            address = file.read()
    return address


def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


# Assets routes
@app.route("/assets/<path:path>")
def send_report(path):
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

    return render_template("404.html"), 404

def getClientIP(request):
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.remote_addr
    return ip

def getVersion():
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


# region Special routes
@app.route("/meet")
@app.route("/meeting")
@app.route("/appointment")
def meet():
    return redirect(
        "https://cloud.woodburn.au/apps/calendar/appointment/PamrmmspWJZr", code=302
    )


@app.route("/links")
def links():
    return render_template("link.html")


@app.route("/sitemap")
@app.route("/sitemap.xml")
def sitemap():
    # Remove all .html from sitemap
    with open("templates/sitemap.xml") as file:
        sitemap = file.read()

    sitemap = sitemap.replace(".html", "")
    return make_response(sitemap, 200, {"Content-Type": "application/xml"})


@app.route("/favicon.png")
def faviconPNG():
    return send_from_directory("templates/assets/img/favicon", "favicon.png")


@app.route("/favicon.svg")
def faviconSVG():
    return send_from_directory("templates/assets/img/favicon", "favicon.svg")

@app.route("/favicon.ico")
def faviconICO():
    return send_from_directory("templates/assets/img/favicon", "favicon.ico")


@app.route("/https.js")
@app.route("/handshake.js")
@app.route("/redirect.js")
def handshake():
    # return request.path
    return send_from_directory("templates/assets/js", request.path.split("/")[-1])


@app.route("/generator/")
def removeTrailingSlash():
    return render_template(request.path.split("/")[-2] + ".html")


@app.route("/.well-known/wallets/<path:path>")
def wallet(path):
    if path[0] == "." and 'proof' not in path:
        return send_from_directory(
            ".well-known/wallets", path, mimetype="application/json"
        )
    elif os.path.isfile(".well-known/wallets/" + path):
        address = ""
        with open(".well-known/wallets/" + path) as file:
            address = file.read()
        address = address.strip()
        return make_response(address, 200, {"Content-Type": "text/plain"})

    if os.path.isfile(".well-known/wallets/" + path.upper()):
        return redirect("/.well-known/wallets/" + path.upper(), code=302)

    return render_template("404.html"), 404


@app.route("/.well-known/nostr.json")
def nostr():
    # Get name parameter
    name = request.args.get("name")
    if name:
        return jsonify(
            {
                "names": {
                    name: "b57b6a06fdf0a4095eba69eee26e2bf6fa72bd1ce6cbe9a6f72a7021c7acaa82"
                }
            }
        )
    return jsonify(
        {
            "names": {
                "nathan": "b57b6a06fdf0a4095eba69eee26e2bf6fa72bd1ce6cbe9a6f72a7021c7acaa82",
                "_": "b57b6a06fdf0a4095eba69eee26e2bf6fa72bd1ce6cbe9a6f72a7021c7acaa82",
            }
        }
    )


@app.route("/.well-known/xrp-ledger.toml")
def xrpLedger():
    # Create a response with the xrp-ledger.toml file
    with open(".well-known/xrp-ledger.toml") as file:
        toml = file.read()

    response = make_response(toml, 200, {"Content-Type": "application/toml"})
    # Set cors headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


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
def pw():
    return send_from_directory("pwa", "sw.js")


# region Sol Links
@app.route("/actions.json")
def actionsJson():
    return jsonify(
        {"rules": [{"pathPattern": "/donate**", "apiPath": "/api/donate**"}]}
    )


@app.route("/api/donate", methods=["GET", "OPTIONS"])
def donateAPI():

    data = {
        "icon": "https://nathan.woodburn.au/assets/img/profile.png",
        "label": "Donate to Nathan.Woodburn/",
        "title": "Donate to Nathan.Woodburn/",
        "description": "Student, developer, and crypto enthusiast",
        "links": {
            "actions": [
                {"label": "0.01 SOL", "href": "/api/donate/0.01"},
                {"label": "0.1 SOL", "href": "/api/donate/0.1"},
                {"label": "1 SOL", "href": "/api/donate/1"},
                {
                    "href": "/api/donate/{amount}",
                    "label": "Donate",
                    "parameters": [
                        {"name": "amount", "label": "Enter a custom SOL amount"}
                    ],
                },
            ]
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Action-Version": "2.4.2",
        "X-Blockchain-Ids": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
    }
    response = make_response(jsonify(data), 200, headers)
    

    if request.method == "OPTIONS":
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type,Authorization,Content-Encoding,Accept-Encoding,X-Action-Version,X-Blockchain-Ids"
        )

    return response


@app.route("/api/donate/<amount>")
def donateAmount(amount):
    data = {
        "icon": "https://nathan.woodburn.au/assets/img/profile.png",
        "label": f"Donate {amount} SOL to Nathan.Woodburn/",
        "title": "Donate to Nathan.Woodburn/",
        "description": f"Donate {amount} SOL to Nathan.Woodburn/",
    }
    return jsonify(data)


@app.route("/api/donate/<amount>", methods=["POST"])
def donateAmountPost(amount):
    if not request.json:
        return jsonify({"message": "Error: No JSON data provided"})

    if "account" not in request.json:
        return jsonify({"message": "Error: No account provided"})

    sender = request.json["account"]

    headers = {
        "Content-Type": "application/json",
        "X-Action-Version": "2.4.2",
        "X-Blockchain-Ids": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
    }

    # Make sure amount is a number
    try:
        amount = float(amount)
    except:
        return jsonify({"message": "Error: Invalid amount"}), 400, headers
    
    if amount < 0.0001:
        return jsonify({"message": "Error: Amount too small"}), 400, headers
        

    # Create transaction
    sender = Pubkey.from_string(sender)
    receiver = Pubkey.from_string("AJsPEEe6S7XSiVcdZKbeV8GRp1QuhFUsG8mLrqL4XgiU")
    transfer_ix = transfer(
        TransferParams(
            from_pubkey=sender, to_pubkey=receiver, lamports=int(amount * 1000000000)
        )
    )
    solana_client = Client("https://api.mainnet-beta.solana.com")
    blockhashData = solana_client.get_latest_blockhash()
    blockhash = blockhashData.value.blockhash

    msg = MessageV0.try_compile(
        payer=sender,
        instructions=[transfer_ix],
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash,
    )
    tx = VersionedTransaction(message=msg, keypairs=[NullSigner(sender)])
    tx = bytes(tx).hex()
    raw_bytes = binascii.unhexlify(tx)
    base64_string = base64.b64encode(raw_bytes).decode("utf-8")

    return jsonify({"message": "Success", "transaction": base64_string}), 200, headers


# endregion

#region Other API routes
@app.route("/api/version")
def version():
    return jsonify({"version": getVersion()})

@app.route("/api/help")
def help():
    return jsonify({
        "message": "Welcome to Nathan.Woodburn/ API! This is a personal website. For more information, visit https://nathan.woodburn.au",
        "endpoints": {
            "/api/time": "Get the current time",
            "/api/timezone": "Get the current timezone",
            "/api/message": "Get the message from the config",
            "/api/ip": "Get your IP address",
            "/api/v1/project": "Get the current project from git",
            "/api/version": "Get the current version of the website"
        },
        "version": getVersion()
    })




@app.route("/api/time")
def time():
    timezone_offset = datetime.timedelta(hours=ncConfig["time-zone"])
    timezone = datetime.timezone(offset=timezone_offset)
    time = datetime.datetime.now(tz=timezone)
    return jsonify({
        "timestring": time.strftime("%A, %B %d, %Y %I:%M %p"),
        "timestamp": time.timestamp(),
        "timezone": ncConfig["time-zone"],
        "timeISO": time.isoformat()
        })


@app.route("/api/timezone")
def timezone():
    return jsonify({"timezone": ncConfig["time-zone"]})

@app.route("/api/timezone", methods=["POST"])
def timezonePost():
    # Refresh config
    global ncConfig
    conf = requests.get("https://cloud.woodburn.au/s/4ToXgFe3TnnFcN7/download/website-conf.json")
    if conf.status_code != 200:
        return jsonify({"message": "Error: Could not get timezone"})
    if not conf.json():
        return jsonify({"message": "Error: Could not get timezone"})
    conf = conf.json()
    if "time-zone" not in conf:
        return jsonify({"message": "Error: Could not get timezone"})
    
    ncConfig = conf
    return jsonify({"message": "Successfully pulled latest timezone", "timezone": ncConfig["time-zone"]})

@app.route("/api/message")
def nc():
    return jsonify({"message": ncConfig["message"]})

@app.route("/api/ip")
def ip():
    return jsonify({"ip": getClientIP(request)})


@app.route("/api/email", methods=["POST"])
def email():
    # Verify json
    if not request.is_json:
        return jsonify({
            "status": 400,
            "error": "Bad request JSON Data missing"
        })

    # Check if api key sent
    data = request.json
    if "key" not in data:
        return jsonify({
            "status": 401,
            "error": "Unauthorized 'key' missing"
        })

    if data["key"] != os.getenv("EMAIL_KEY"):
        return jsonify({
            "status": 401,
            "error": "Unauthorized 'key' invalid"
        })

    return sendEmail(data)

@app.route("/api/v1/project")
def getCurrentProject():
    try:
        git = requests.get(
            "https://git.woodburn.au/api/v1/users/nathanwoodburn/activities/feeds?only-performed-by=true&limit=1",
            headers={"Authorization": os.getenv("git_token")},
        )
        git = git.json()
        git = git[0]
        repo_name = git["repo"]["name"]
        repo_name = repo_name.lower()
        repo_description = git["repo"]["description"]
    except:
        repo_name = "nathanwoodburn.github.io"
        repo_description = "Personal website"
        git = {
            "repo": {
                "html_url": "https://nathan.woodburn.au",
                "name": "nathanwoodburn.github.io",
                "description": "Personal website",
            }
        }
        print("Error getting git data")
    
    return jsonify({
        "repo_name": repo_name,
        "repo_description": repo_description,
        "git": git,
    })

    
    

#endregion
# endregion


# region Main routes
@app.route("/")
def index():
    global handshake_scripts
    global projects
    global projectsUpdated

    # Check if host if podcast.woodburn.au
    if "podcast.woodburn.au" in request.host:
        return render_template("podcast.html")

    loaded = False
    if request.referrer:
        # Check if referrer includes nathan.woodburn.au
        if "nathan.woodburn.au" in request.referrer:
            loaded = True

    # Check if crawler
    if request.headers and request.headers.get("User-Agent"):
        # Check if curl
        if "curl" in request.headers.get("User-Agent"):
            return jsonify(
                {
                    "message": "Welcome to Nathan.Woodburn/! This is a personal website. For more information, visit https://nathan.woodburn.au",
                    "ip": getClientIP(request),
                    "dev": handshake_scripts == "",
                    "version": getVersion()
                }
            )

        if "Googlebot" not in request.headers.get(
            "User-Agent"
        ) and "Bingbot" not in request.headers.get("User-Agent"):
            # Check if cookie is set
            if not request.cookies.get("loaded") and not loaded:
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
            headers={"Authorization": os.getenv("git_token")},
        )
        git = git.json()
        git = git[0]
        repo_name = git["repo"]["name"]
        repo_name = repo_name.lower()
        repo_description = git["repo"]["description"]
    except:
        repo_name = "nathanwoodburn.github.io"
        repo_description = "Personal website"
        git = {
            "repo": {
                "html_url": "https://nathan.woodburn.au",
                "name": "nathanwoodburn.github.io",
                "description": "Personal website",
            }
        }
        print("Error getting git data")

    # Get only repo names for the newest updates
    if projects == [] or projectsUpdated < datetime.datetime.now() - datetime.timedelta(
        hours=2
    ):
        projectsreq = requests.get(
            "https://git.woodburn.au/api/v1/users/nathanwoodburn/repos"
        )

        projects = projectsreq.json()

        # Check for next page
        pageNum = 1
        while 'rel="next"' in projectsreq.headers["link"]:
            projectsreq = requests.get(
                "https://git.woodburn.au/api/v1/users/nathanwoodburn/repos?page="
                + str(pageNum)
            )
            projects += projectsreq.json()
            pageNum += 1

        for project in projects:
            if (
                project["avatar_url"] == "https://git.woodburn.au/"
                or project["avatar_url"] == ""
            ):
                project["avatar_url"] = "/favicon.png"
            project["name"] = project["name"].replace("_", " ").replace("-", " ")
        # Sort by last updated
        projectsList = sorted(projects, key=lambda x: x["updated_at"], reverse=True)
        projects = []
        projectNames = []
        projectNum = 0
        while len(projects) < 3:
            if projectsList[projectNum]["name"] not in projectNames:
                projects.append(projectsList[projectNum])
                projectNames.append(projectsList[projectNum]["name"])
            projectNum += 1
        projectsUpdated = datetime.datetime.now()

    custom = ""
    # Check for downtime
    uptime = requests.get("https://uptime.woodburn.au/api/status-page/main/badge")
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
    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""

    # Get time
    timezone_offset = datetime.timedelta(hours=ncConfig["time-zone"])
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
    time += f"startClock({ncConfig['time-zone']});"
    time += "</script>"

    HNSaddress = getAddress("HNS")
    SOLaddress = getAddress("SOL")
    BTCaddress = getAddress("BTC")
    ETHaddress = getAddress("ETH")
    # Set cookie
    resp = make_response(
        render_template(
            "index.html",
            handshake_scripts=handshake_scripts,
            HNS=HNSaddress,
            SOL=SOLaddress,
            BTC=BTCaddress,
            ETH=ETHaddress,
            repo=repo,
            repo_description=repo_description,
            custom=custom,
            sites=sites,
            projects=projects,
            time=time,
            message=ncConfig["message"],
        ),
        200,
        {"Content-Type": "text/html"},
    )
    resp.set_cookie("loaded", "true", max_age=604800)

    return resp


# region Now Pages
@app.route("/now")
@app.route("/now/")
def now_page():
    global handshake_scripts

    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""

    return now.render_latest_now(handshake_scripts)


@app.route("/now/<path:path>")
def now_path(path):
    global handshake_scripts
    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""

    return now.render_now_page(path,handshake_scripts)


@app.route("/old")
@app.route("/old/")
@app.route("/now/old")
@app.route("/now/old/")
def now_old():
    global handshake_scripts
    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""

    now_dates = now.list_now_dates()[1:]
    html = '<ul class="list-group">'
    html += f'<a style="text-decoration:none;" href="/now"><li class="list-group-item" style="background-color:#000000;color:#ffffff;">{now.get_latest_now_date(True)}</li></a>'

    for date in now_dates:
        link = date
        date = datetime.datetime.strptime(date, "%y_%m_%d")
        date = date.strftime("%A, %B %d, %Y")
        html += f'<a style="text-decoration:none;" href="/now/{link}"><li class="list-group-item" style="background-color:#000000;color:#ffffff;">{date}</li></a>'

    html += "</ul>"
    return render_template(
        "now/old.html", handshake_scripts=handshake_scripts, now_pages=html
    )

@app.route("/now.rss")
@app.route("/now.xml")
@app.route("/rss.xml")
def now_rss():
    host = "https://" + request.host
    if ":" in request.host:
        host = "http://" + request.host
    # Generate RSS feed
    now_pages = now.list_now_page_files()
    rss = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Nathan.Woodburn/</title><link>{host}</link><description>See what I\'ve been up to</description><language>en-us</language><lastBuildDate>{datetime.datetime.now(tz=datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")}</lastBuildDate><atom:link href="{host}/now.rss" rel="self" type="application/rss+xml" />'
    for page in now_pages:
        link = page.strip(".html")
        date = datetime.datetime.strptime(link, "%y_%m_%d")
        date = date.strftime("%A, %B %d, %Y")
        rss += f'<item><title>What\'s Happening {date}</title><link>{host}/now/{link}</link><description>Latest updates for {date}</description><guid>{host}/now/{link}</guid></item>'
    rss += "</channel></rss>"
    return make_response(rss, 200, {"Content-Type": "application/rss+xml"})

@app.route("/now.json")
def now_json():
    now_pages = now.list_now_page_files()
    host = "https://" + request.host
    if ":" in request.host:
        host = "http://" + request.host
    now_pages = [{"url":host+"/now/"+page.strip(".html"), "date":datetime.datetime.strptime(page.strip(".html"), "%y_%m_%d").strftime("%A, %B %d, %Y"), "title":"What's Happening "+datetime.datetime.strptime(page.strip(".html"), "%y_%m_%d").strftime("%A, %B %d, %Y")} for page in now_pages]
    return jsonify(now_pages)

# endregion

# region blog Pages
@app.route("/blog")
@app.route("/blog/")
def blog_page():
    global handshake_scripts

    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""

    return blog.render_blog_home(handshake_scripts)


@app.route("/blog/<path:path>")
def blog_path(path):
    global handshake_scripts
    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""

    return blog.render_blog_page(path,handshake_scripts)

#TODO add rss json and xml for blog
# @app.route("/blog.rss")
# @app.route("/blog.xml")
# @app.route("/rss.xml")
# def blog_rss():
#     host = "https://" + request.host
#     if ":" in request.host:
#         host = "http://" + request.host
#     # Generate RSS feed
#     blog_pages = blog.list_blog_page_files()
#     rss = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Nathan.Woodburn/</title><link>{host}</link><description>See what I\'ve been up to</description><language>en-us</language><lastBuildDate>{datetime.datetime.blog(tz=datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")}</lastBuildDate><atom:link href="{host}/blog.rss" rel="self" type="application/rss+xml" />'
#     for page in blog_pages:
#         link = page.strip(".html")
#         date = datetime.datetime.strptime(link, "%y_%m_%d")
#         date = date.strftime("%A, %B %d, %Y")
#         rss += f'<item><title>What\'s Happening {date}</title><link>{host}/blog/{link}</link><description>Latest updates for {date}</description><guid>{host}/blog/{link}</guid></item>'
#     rss += "</channel></rss>"
#     return make_response(rss, 200, {"Content-Type": "application/rss+xml"})

# @app.route("/blog.json")
# def blog_json():
#     blog_pages = blog.list_blog_page_files()
#     host = "https://" + request.host
#     if ":" in request.host:
#         host = "http://" + request.host
#     blog_pages = [{"url":host+"/blog/"+page.strip(".html"), "date":datetime.datetime.strptime(page.strip(".html"), "%y_%m_%d").strftime("%A, %B %d, %Y"), "title":"What's Happening "+datetime.datetime.strptime(page.strip(".html"), "%y_%m_%d").strftime("%A, %B %d, %Y")} for page in blog_pages]
#     return jsonify(blog_pages)

# endregion



# region Donate
@app.route("/donate")
def donate():
    global handshake_scripts
    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""

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
            handshake_scripts=handshake_scripts,
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

    if os.path.isfile(f".well-known/wallets/.domains"):
        # Get json of all domains
        with open(f".well-known/wallets/.domains") as file:
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
        handshake_scripts=handshake_scripts,
        crypto=cryptoHTML,
        coins=coins,
        default_coins=default_coins,
    )


@app.route("/address/<path:address>")
def addressQR(address:str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(address)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="#110033", back_color="white")

    # Save the QR code image to a temporary file
    qr_image_path = "/tmp/qr_code.png"
    qr_image.save(qr_image_path)

    # Return the QR code image as a response
    return send_file(qr_image_path, mimetype="image/png")


@app.route("/qrcode/<path:data>")
@app.route("/qr/<path:data>")
def qr(data:str):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=10,border=2)
    qr.add_data(data)
    qr.make()

    qr_image:Image.Image = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Add logo
    logo = Image.open("templates/assets/img/favicon/logo.png")
    basewidth = qr_image.size[0]//3
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth, hsize),Image.Resampling.LANCZOS)
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

@app.route("/download/<path:path>")
def download(path):
    # Check if file exists
    if path in downloads:
        path = downloads[path]
    if os.path.isfile(path):
        return send_file(path)
    return render_template("404.html"), 404

@app.route("/.well-known/<path:path>")
def wellknown(path):
    return send_from_directory(".well-known", path)


@app.route("/<path:path>")
def catch_all(path: str):
    global handshake_scripts
    # If localhost, don't load handshake
    if (
        request.host == "localhost:5000"
        or request.host == "127.0.0.1:5000"
        or os.getenv("dev") == "true"
        or request.host == "test.nathan.woodburn.au"
    ):
        handshake_scripts = ""

    if path.lower().replace(".html", "") in restricted:
        return render_template("404.html"), 404

    if path in redirects:
        return redirect(redirects[path], code=302)

    # If file exists, load it
    if os.path.isfile("templates/" + path):
        return render_template(path, handshake_scripts=handshake_scripts, sites=sites)

    # Try with .html
    if os.path.isfile("templates/" + path + ".html"):
        return render_template(
            path + ".html", handshake_scripts=handshake_scripts, sites=sites
        )

    if os.path.isfile("templates/" + path.strip("/") + ".html"):
        return render_template(
            path.strip("/") + ".html", handshake_scripts=handshake_scripts, sites=sites
        )

    # Try to find a file matching
    if path.count("/") < 1:
        # Try to find a file matching
        filename = find(path, "templates")
        if filename:
            return send_file(filename)

    if request.headers:
        # Check if curl
        if "curl" in request.headers.get("User-Agent"):
            return jsonify(
                {
                    "status": 404,
                    "message": "Page not found",
                    "ip": getClientIP(request),
                }
            ), 404
    return render_template("404.html"), 404

@app.route("/resume.pdf")
def resume_pdf():
    # Check if file exists
    if os.path.isfile("data/resume.pdf"):
        return send_file("data/resume.pdf")
    return render_template("404.html"), 404


# endregion


# region ACME
@app.route("/hnsdoh-acme", methods=["POST"])
def hnsdoh_acme():
    print(f"ACME request from {getClientIP(request)}")

    # Get the TXT record from the request
    if not request.json:
        print("No JSON data provided for ACME")
        return jsonify({"status": "error", "error": "No JSON data provided"})
    if "txt" not in request.json or "auth" not in request.json:
        print("Missing required data for ACME")
        return jsonify({"status": "error", "error": "Missing required data"})

    txt = request.json["txt"]
    auth = request.json["auth"]
    if auth != os.getenv("CF_AUTH"):
        print("Invalid auth for ACME")
        return jsonify({"status": "error", "error": "Invalid auth"})

    cf = Cloudflare(api_token=os.getenv("CF_TOKEN"))
    zone = cf.zones.list(name="hnsdoh.com").to_dict()
    zone_id = zone["result"][0]["id"]
    existing_records = cf.dns.records.list(
        zone_id=zone_id, type="TXT", name="_acme-challenge.hnsdoh.com"
    ).to_dict()
    record_id = existing_records["result"][0]["id"]
    cf.dns.records.delete(dns_record_id=record_id, zone_id=zone_id)
    cf.dns.records.create(
        zone_id=zone_id,
        type="TXT",
        name="_acme-challenge",
        content=txt,
    )
    print(f"ACME request successful: {txt}")
    return jsonify({"status": "success"})


# endregion


# region Podcast
@app.route("/ID1")
def ID1():
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1")
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@app.route("/ID1/")
def ID1_slash():
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1/")
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@app.route("/ID1/<path:path>")
def ID1_path(path):
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1/" + path)
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@app.route("/ID1.xml")
def ID1_xml():
    # Proxy to ID1 url
    req = requests.get("https://podcasts.c.woodburn.au/ID1.xml")
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


@app.route("/podsync.opml")
def podsync():
    req = requests.get("https://podcasts.c.woodburn.au/podsync.opml")
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


# endregion


# region Error Catching
# 404 catch all
@app.errorhandler(404)
def not_found(e):
    if request.headers:
        # Check if curl
        if "curl" in request.headers.get("User-Agent"):
            return jsonify(
                {
                    "status": 404,
                    "message": "Page not found",
                    "ip": getClientIP(request),
                }
            ), 404

    return render_template("404.html"), 404


# endregion

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="127.0.0.1")
