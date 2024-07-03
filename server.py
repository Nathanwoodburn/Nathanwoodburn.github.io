import json
from flask import Flask, make_response, redirect, request, jsonify, render_template, send_from_directory, send_file
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
from solana.transaction import Transaction
from solders.hash import Hash
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.null_signer import NullSigner

app = Flask(__name__)
CORS(app)

dotenv.load_dotenv()

handshake_scripts = '<script src="https://nathan.woodburn/handshake.js" domain="nathan.woodburn" async></script><script src="https://nathan.woodburn/https.js" async></script>'

restricted = ['ascii']

sites = []
if os.path.isfile('data/sites.json'):
    with open('data/sites.json') as file:
        sites = json.load(file)
        # Remove any sites that are not enabled
        sites = [site for site in sites if 'enabled' not in site or site['enabled'] == True]

projects = []
projectsUpdated = 0

@cache
def getAddress(coin:str) -> str:
    address = ''
    if os.path.isfile('.well-known/wallets/' + coin.upper()):
        with open('.well-known/wallets/' + coin.upper()) as file:
            address = file.read()
    return address

#Assets routes
@app.route('/assets/<path:path>')
def send_report(path):
    if path.endswith('.json'):
        return send_from_directory('templates/assets', path, mimetype='application/json')

    if os.path.isfile('templates/assets/' + path):
        return send_from_directory('templates/assets', path)
    
    # Custom matching for images
    pathMap = {
        "img/hns/w": "img/external/HNS/white",
        "img/hns/b": "img/external/HNS/black",
        "img/hns": "img/external/HNS/black",
    }

    for key in pathMap:
        print(path, key)
        if path.startswith(key):
            tmpPath = path.replace(key, pathMap[key])
            print(tmpPath)
            if os.path.isfile('templates/assets/' + tmpPath):
                return send_from_directory('templates/assets', tmpPath)
            

    # Try looking in one of the directories
    filename:str = path.split('/')[-1]
    if filename.endswith('.png') or filename.endswith('.jpg') \
        or filename.endswith('.jpeg') or filename.endswith('.svg'):
        if os.path.isfile('templates/assets/img/' + filename):
            return send_from_directory('templates/assets/img', filename)
        if os.path.isfile('templates/assets/img/favicon/' + filename):
            return send_from_directory('templates/assets/img/favicon', filename)

    return render_template('404.html'), 404


# Special routes
@app.route('/links')
def links():
    return render_template('link.html')

@app.route('/sitemap')
@app.route('/sitemap.xml')
def sitemap():
    # Remove all .html from sitemap
    with open('templates/sitemap.xml') as file:
        sitemap = file.read()

    sitemap = sitemap.replace('.html', '')
    return make_response(sitemap, 200, {'Content-Type': 'application/xml'})

@app.route('/favicon.png')
def faviconPNG():
    return send_from_directory('templates/assets/img/favicon', 'favicon.png')

@app.route('/favicon.svg')
def faviconSVG():
    return send_from_directory('templates/assets/img/favicon', 'favicon.svg')

@app.route('/https.js')
@app.route('/handshake.js')
@app.route('/redirect.js')
def handshake():
    # return request.path
    return send_from_directory('templates/assets/js', request.path.split('/')[-1])

@app.route('/generator/')
def removeTrailingSlash():
    return render_template(request.path.split('/')[-2] + '.html')

@app.route('/.well-known/wallets/<path:path>')
def wallet(path):
    if path[0] == ".":
        return send_from_directory('.well-known/wallets', path, mimetype='application/json')
    elif os.path.isfile('.well-known/wallets/' + path):
        address = ''
        with open('.well-known/wallets/' + path) as file:
            address = file.read()
        address = address.strip()
        return make_response(address, 200, {'Content-Type': 'text/plain'})

    if os.path.isfile('.well-known/wallets/' + path.upper()):
        return redirect('/.well-known/wallets/' + path.upper(), code=302)

    return render_template('404.html'), 404

@app.route('/.well-known/nostr.json')
def nostr():
    # Get name parameter
    name = request.args.get('name')
    if not name:
        return jsonify({'error': 'No name provided'})
    return jsonify({
        'names': {
            name: 'b57b6a06fdf0a4095eba69eee26e2bf6fa72bd1ce6cbe9a6f72a7021c7acaa82'
        }
    })

@app.route('/.well-known/xrp-ledger.toml')
def xrpLedger():
    # Create a response with the xrp-ledger.toml file
    with open('.well-known/xrp-ledger.toml') as file:
        toml = file.read()
    
    response = make_response(toml, 200, {'Content-Type': 'application/toml'})
    # Set cors headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response



@app.route('/manifest.json')
def manifest():
    host = request.host
    if host == 'nathan.woodburn.au':
        return send_from_directory('templates', 'manifest.json')
    
    # Read as json
    with open('templates/manifest.json') as file:
        manifest = json.load(file)
    if host != 'localhost:5000' and host != '127.0.0.1:5000':
        manifest['start_url'] = f'https://{host}/'
    else:
        manifest['start_url'] = 'http://127.0.0.1:5000/'
    return jsonify(manifest)

# region Sol Links
@app.route('/actions.json')
def actionsJson():
    return jsonify({
        "rules": [
            {
                "pathPattern":"/donate**",
                "apiPath":"/api/donate**"
            }
        ]})

@app.route('/api/donate')
def donateAPI():
    data = {
        "icon": "https://nathan.woodburn.au/assets/img/profile.png",
        "label": "1 SOL",
        "title": "Donate to Nathan.Woodburn/",
        "description": "Student, developer, and crypto enthusiast",
        "links": {
            "actions": [
                {
                    "label": "0.01 SOL",
                    "href": "/api/donate/0.01"
                },
                {
                    "label": "0.1 SOL",
                    "href": "/api/donate/0.1"
                },
                {
                    "label": "1 SOL",
                    "href": "/api/donate/1"
                },
                {
                    "href": "/api/donate/{amount}",
                    "label": "Donate",
                    "parameters": [
                        {
                            "name": "amount",
                            "label": "Enter a custom SOL amount"
                        }
                    ]
                }
            ]
        }
    }
    return jsonify(data)

@app.route('/api/donate/<amount>')
def donateAmount(amount):
    data = {
        "icon": "https://nathan.woodburn.au/assets/img/profile.png",
        "label": f"{amount} SOL",
        "title": "Donate to Nathan.Woodburn/",
        "description": "Student, developer, and crypto enthusiast"
    }
    return jsonify(data)

@app.route('/api/donate/<amount>', methods=['POST'])
def donateAmountPost(amount):
    if not request.json:
        return jsonify({'message': 'Error: No JSON data provided'})

    if 'account' not in request.json:
        return jsonify({'message': 'Error: No account provided'})

    sender = request.json['account']

    # Make sure amount is a number
    try:
        amount = float(amount)
    except:
        return jsonify({'message': 'Error: Invalid amount'})
    
    # Create transaction
    sender = Pubkey.from_string(sender)
    receiver = Pubkey.from_string('AJsPEEe6S7XSiVcdZKbeV8GRp1QuhFUsG8mLrqL4XgiU')
    transfer_ix = transfer(TransferParams(from_pubkey=sender, to_pubkey=receiver, lamports=int(amount * 1000000000)))
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
    base64_string = base64.b64encode(raw_bytes).decode('utf-8')

    return jsonify({'message': 'Success', 'transaction': base64_string})
    

    

# endregion

# region Main routes
@app.route('/')
def index():
    # Check if host if podcast.woodburn.au
    if "podcast.woodburn.au" in request.host:
        return render_template('podcast.html')
    
    loaded = False
    if request.referrer:
        # Check if referrer includes nathan.woodburn.au
        if "nathan.woodburn.au" in request.referrer:
            loaded = True
            

    # Check if crawler
    if request.user_agent.browser != 'Googlebot' and request.user_agent.browser != 'Bingbot':
        # Check if cookie is set
        if not request.cookies.get('loaded') and not loaded:
            # Set cookie
            resp = make_response(render_template('loading.html'), 200, {'Content-Type': 'text/html'})
            resp.set_cookie('loaded', 'true', max_age=604800)
            return resp
        

    global handshake_scripts
    global projects
    global projectsUpdated

    try:
        git=requests.get('https://git.woodburn.au/api/v1/users/nathanwoodburn/activities/feeds?only-performed-by=true&limit=1',
                         headers={'Authorization': os.getenv('git_token')})
        git = git.json()
        git = git[0]
        repo_name=git['repo']['name']
        repo_name=repo_name.lower()
        repo_description=git['repo']['description']
    except:
        repo_name = "nathanwoodburn.github.io"
        repo_description = "Personal website"
        git = {'repo': {'html_url': 'https://nathan.woodburn.au', 'name': 'nathanwoodburn.github.io', 'description': 'Personal website'}}
        print("Error getting git data")
    
    # Get only repo names for the newest updates
    if projects == [] or projectsUpdated < datetime.datetime.now() - datetime.timedelta(hours=2):
        projectsreq = requests.get('https://git.woodburn.au/api/v1/users/nathanwoodburn/repos')
        
        projects = projectsreq.json()

        # Check for next page
        pageNum = 1
        while 'rel="next"' in projectsreq.headers['link']:
            projectsreq = requests.get('https://git.woodburn.au/api/v1/users/nathanwoodburn/repos?page=' + str(pageNum))
            projects += projectsreq.json()
            pageNum += 1
        
        
        for project in projects:
            if project['avatar_url'] == 'https://git.woodburn.au/':
                project['avatar_url'] = '/favicon.png'
            project['name'] = project['name'].replace('_', ' ').replace('-', ' ')
        # Sort by last updated
        projectsList = sorted(projects, key=lambda x: x['updated_at'], reverse=True)
        projects = []
        projectNames = []
        projectNum = 0
        while len(projects) < 3:
            if projectsList[projectNum]['name'] not in projectNames:
                projects.append(projectsList[projectNum])
                projectNames.append(projectsList[projectNum]['name'])
            projectNum += 1
        projectsUpdated = datetime.datetime.now()

    custom = ""
    # Check for downtime
    uptime = requests.get('https://uptime.woodburn.au/api/status-page/main/badge')
    uptime = uptime.content.count(b'Up') > 1

    if uptime:
        custom += "<style>#downtime{display:none !important;}</style>"
    else:
        custom += "<style>#downtime{opacity:1;}</style>"
    # Special names
    if repo_name == "nathanwoodburn.github.io":
        repo_name = "Nathan.Woodburn/"

    html_url=git['repo']['html_url']
    repo = "<a href=\"" + html_url + "\" target=\"_blank\">" + repo_name + "</a>"
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true" or request.host == "test.nathan.woodburn.au":
        handshake_scripts = ""

    HNSaddress = getAddress("HNS")
    SOLaddress = getAddress("SOL")
    BTCaddress = getAddress("BTC")
    ETHaddress = getAddress("ETH")
    # Set cookie
    resp = make_response(render_template('index.html', handshake_scripts=handshake_scripts,
                                         HNS=HNSaddress, SOL=SOLaddress, BTC=BTCaddress,
                                         ETH=ETHaddress, repo=repo,
                                         repo_description=repo_description,
                                         custom=custom,sites=sites,projects=projects), 200, {'Content-Type': 'text/html'})
    resp.set_cookie('loaded', 'true', max_age=604800)

    return resp


# region Now Pages
@app.route('/now')
@app.route('/now/')
def now():
    global handshake_scripts
    
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true" or request.host == "test.nathan.woodburn.au":
        handshake_scripts = ""
    
    # Get latest now page
    files = os.listdir('templates/now')
    # Remove template
    files = [file for file in files if file != 'template.html' and file != 'old.html']
    files.sort(reverse=True)
    date = files[0].strip('.html')
    # Convert to date
    date = datetime.datetime.strptime(date, '%y_%m_%d')
    date = date.strftime('%A, %B %d, %Y')
    return render_template('now/' + files[0], handshake_scripts=handshake_scripts, DATE=date)

@app.route('/now/<path:path>')
def now_path(path):
    global handshake_scripts
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true" or request.host == "test.nathan.woodburn.au":
        handshake_scripts = ""

    date = path
    date = date.strip('.html')

    try:
        # Convert to date
        date = datetime.datetime.strptime(date, '%y_%m_%d')
        date = date.strftime('%A, %B %d, %Y')
    except:
        date = ""
    
    if path.lower().replace('.html','') == 'template':
        return render_template('404.html'), 404

    # If file exists, load it
    if os.path.isfile('templates/now/' + path):
        return render_template('now/' + path, handshake_scripts=handshake_scripts, DATE=date)
    if os.path.isfile('templates/now/' + path + '.html'):
        return render_template('now/' + path + '.html', handshake_scripts=handshake_scripts, DATE=date)
    
    return render_template('404.html'), 404

@app.route('/old')
@app.route('/old/')
@app.route('/now/old')
@app.route('/now/old/')
def now_old():
    global handshake_scripts
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true" or request.host == "test.nathan.woodburn.au":
        handshake_scripts = ""

    now_pages = os.listdir('templates/now')
    now_pages = [page for page in now_pages if page != 'template.html' and page != 'old.html']
    now_pages.sort(reverse=True)
    html = '<ul class="list-group">'
    latest = " (Latest)"
    for page in now_pages:
        link = page.strip('.html')
        date = datetime.datetime.strptime(link, '%y_%m_%d')
        date = date.strftime('%A, %B %d, %Y')
        html += f'<a style="text-decoration:none;" href="/now/{link}"><li class="list-group-item" style="background-color:#000000;color:#ffffff;">{date}{latest}</li></a>'
        latest = ""

    html += '</ul>'
    return render_template('now/old.html', handshake_scripts=handshake_scripts,now_pages=html)
# endregion


@app.route('/donate')
def donate():
    global handshake_scripts
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true" or request.host == "test.nathan.woodburn.au":
        handshake_scripts = ""

    coinList = os.listdir('.well-known/wallets')
    coinList = [file for file in coinList if file[0] != '.']
    coinList.sort()

    tokenList = []

    with open('.well-known/wallets/.tokens') as file:
        tokenList = file.read()
        tokenList = json.loads(tokenList)

    coinNames = {}
    with open('.well-known/wallets/.coins') as file:
        coinNames = file.read()
        coinNames = json.loads(coinNames)

    coins = ''
    default_coins = ['btc', 'eth', 'hns','sol','xrp','ada','dot']


    for file in coinList:
        if file in coinNames:
            coins += f'<a class="dropdown-item" style="{"display:none;" if file.lower() not in default_coins else ""}" href="?c={file.lower()}">{coinNames[file]}</a>'
        else:
            coins += f'<a class="dropdown-item" style="{"display:none;" if file.lower() not in default_coins else ""}" href="?c={file.lower()}">{file}</a>'

    for token in tokenList:
        if token["chain"] != 'null':
            coins += f'<a class="dropdown-item" style="display:none;" href="?t={token["symbol"].lower()}&c={token["chain"].lower()}">{token["name"]} ({token["symbol"] + " on " if token["symbol"] != token["name"] else ""}{token["chain"]})</a>'
        else:
           coins += f'<a class="dropdown-item" style="display:none;" href="?t={token["symbol"].lower()}&c={token["chain"].lower()}">{token["name"]} ({token["symbol"] if token["symbol"] != token["name"] else ""})</a>'

    crypto = request.args.get('c')
    if not crypto:
        instructions = '<br>Donate with cryptocurrency:<br>Select a coin from the dropdown above.'
        return render_template('donate.html', handshake_scripts=handshake_scripts, coins=coins,default_coins=default_coins, crypto=instructions)
    crypto = crypto.upper()

    token = request.args.get('t')
    if token:
        token = token.upper()
        for t in tokenList:
            if t['symbol'].upper() == token and t['chain'].upper() == crypto:
                token = t
                break
        if not isinstance(token, dict):
            token = {
                "name": "Unknown token",
                "symbol": token,
                "chain": crypto
            }

    address = ''
    domain = ''
    cryptoHTML = ''
    if os.path.isfile(f'.well-known/wallets/{crypto}'):
        with open(f'.well-known/wallets/{crypto}') as file:
            address = file.read()
            if not token:
                cryptoHTML += f'<br>Donate with {coinNames[crypto] if crypto in coinNames else crypto}:'
            else:
                cryptoHTML += f'<br>Donate with {token["name"]} {"("+token["symbol"]+") " if token["symbol"] != token["name"] else ""}on {crypto}:'
            cryptoHTML += f'<code data-bs-toggle="tooltip" data-bss-tooltip="" id="crypto-address" class="address" style="color: rgb(242,90,5);display: block;" data-bs-original-title="Click to copy">{address}</code>'
    elif token:
        if 'address' in token:
            address = token['address']
            cryptoHTML += f'<br>Donate with {token["name"]} {"("+token["symbol"]+")" if token["symbol"] != token["name"] else ""}{" on "+crypto if crypto != "NULL" else ""}:'
            cryptoHTML += f'<code data-bs-toggle="tooltip" data-bss-tooltip="" id="crypto-address" class="address" style="color: rgb(242,90,5);display: block;" data-bs-original-title="Click to copy">{address}</code>'
        else:
            cryptoHTML += f'<br>Invalid coin: {crypto}<br>'
    else:
        cryptoHTML += f'<br>Invalid coin: {crypto}<br>'
        
        

    if os.path.isfile(f'.well-known/wallets/.domains'):
        # Get json of all domains
        with open(f'.well-known/wallets/.domains') as file:
            domains = file.read()
            domains = json.loads(domains)
            
        if crypto in domains:
            domain = domains[crypto]
            cryptoHTML += '<br>Or send to this domain on compatible wallets:<br>'
            cryptoHTML += f'<code data-bs-toggle="tooltip" data-bss-tooltip="" id="crypto-domain" class="address" style="color: rgb(242,90,5);display: block;" data-bs-original-title="Click to copy">{domain}</code>'
    if address:
        cryptoHTML += '<img src="/qrcode/' + address + '" alt="QR Code" style="width: 100%; max-width: 200px; margin: 20px auto;">'


    copyScript = '<script>document.getElementById("crypto-address").addEventListener("click", function() {navigator.clipboard.writeText(this.innerText);this.setAttribute("data-bs-original-title", "Copied!");});document.getElementById("crypto-domain").addEventListener("click", function() {navigator.clipboard.writeText(this.innerText);this.setAttribute("data-bs-original-title", "Copied!");});</script>'
    cryptoHTML += copyScript

    return render_template('donate.html', handshake_scripts=handshake_scripts, crypto=cryptoHTML, coins=coins,default_coins=default_coins)

@app.route('/qrcode/<path:data>')
def addressQR(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="#110033", back_color="white")


    # Save the QR code image to a temporary file
    qr_image_path = "/tmp/qr_code.png"
    qr_image.save(qr_image_path)

    # Return the QR code image as a response
    return send_file(qr_image_path, mimetype="image/png")

@app.route('/supersecretpath')
def supersecretpath():
    ascii_art = ''
    if os.path.isfile('data/ascii.txt'):
        with open('data/ascii.txt') as file:
            ascii_art = file.read()
        
    converter = Ansi2HTMLConverter()
    ascii_art_html = converter.convert(ascii_art)
    return render_template('ascii.html', ascii_art=ascii_art_html)

@app.route('/<path:path>')
def catch_all(path):
    global handshake_scripts
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true" or request.host == "test.nathan.woodburn.au":
        handshake_scripts = ""

    if path.lower().replace('.html','') in restricted:
        return render_template('404.html'), 404
    # If file exists, load it
    if os.path.isfile('templates/' + path):
        return render_template(path, handshake_scripts=handshake_scripts,sites=sites)
    
    # Try with .html
    if os.path.isfile('templates/' + path + '.html'):
        return render_template(path + '.html', handshake_scripts=handshake_scripts,sites=sites)

    if os.path.isfile('templates/' + path.strip('/') + '.html'):
        return render_template(path.strip('/') + '.html', handshake_scripts=handshake_scripts,sites=sites)

    return render_template('404.html'), 404
# endregion

#region ACME
@app.route('/hnsdoh-acme', methods=['POST'])
def hnsdoh_acme():
    # Get the TXT record from the request
    if not request.json:
        return jsonify({'status': 'error', 'error': 'No JSON data provided'})
    if 'txt' not in request.json or 'auth' not in request.json:
        return jsonify({'status': 'error', 'error': 'Missing required data'})

    txt = request.json['txt']
    auth = request.json['auth']
    if auth != os.getenv('CF_AUTH'):
        return jsonify({'status': 'error', 'error': 'Invalid auth'})

    cf = Cloudflare(api_token=os.getenv('CF_TOKEN'))
    zone = cf.zones.get(params={'name': 'hnsdoh.com'})
    zone_id = zone[0]['id']
    existing_records = cf.zones.dns_records.get(zone_id, params={'type': 'TXT', 'name': '_acme-challenge.hnsdoh.com'})
    
    # Delete existing TXT records
    for record in existing_records:
        print(record)
        record_id = record['id']
        cf.zones.dns_records.delete(zone_id, record_id)
        



    record = cf.zones.dns_records.post(zone_id, data={'type': 'TXT', 'name': '_acme-challenge', 'content': txt})
    print(record)
    return jsonify({'status': 'success'})
#endregion

#region Podcast
@app.route('/ID1')
def ID1():
    # Proxy to ID1 url
    req = requests.get('https://id1.woodburn.au/ID1')
    return make_response(req.content, 200, {'Content-Type': req.headers['Content-Type']})

@app.route('/ID1/')
def ID1_slash():
    # Proxy to ID1 url
    req = requests.get('https://id1.woodburn.au/ID1/')
    return make_response(req.content, 200, {'Content-Type': req.headers['Content-Type']})

@app.route('/ID1/<path:path>')
def ID1_path(path):
    # Proxy to ID1 url
    req = requests.get('https://id1.woodburn.au/ID1/' + path)
    return make_response(req.content, 200, {'Content-Type': req.headers['Content-Type']})

@app.route('/ID1.xml')
def ID1_xml():
    # Proxy to ID1 url
    req = requests.get('https://id1.woodburn.au/ID1.xml')
    return make_response(req.content, 200, {'Content-Type': req.headers['Content-Type']})

@app.route('/podsync.opml')
def podsync():
    req = requests.get('https://id1.woodburn.au/podsync.opml')
    return make_response(req.content, 200, {'Content-Type': req.headers['Content-Type']})
#endregion


#region Error Catching
# 404 catch all
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404
#endregion

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')