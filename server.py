from flask import Flask, make_response, redirect, request, jsonify, render_template, send_from_directory
import os
import dotenv
import requests
import CloudFlare

app = Flask(__name__)
dotenv.load_dotenv()

address = ''
handshake_scripts = '<script src="https://nathan.woodburn/handshake.js" domain="nathan.woodburn" async></script><script src="https://nathan.woodburn/https.js" async></script>'

# Custom header
def add_custom_header(response):
    response.headers['Onion-Location'] = 'http://wdbrncwefot4hd7bdrz5rzb74mefay7zvrjn2vmkpdm44l7fwnih5ryd.onion/'
    return response
app.after_request(add_custom_header)


#Assets routes
@app.route('/assets/<path:path>')
def send_report(path):
    if path.endswith('.json'):
        return send_from_directory('templates/assets', path, mimetype='application/json')

    return send_from_directory('templates/assets', path)


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
    return send_from_directory('templates/assets/img', 'android-chrome-512x512.png')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('templates/assets/img', 'favicon.ico')

@app.route('/favicon.svg')
def faviconSVG():
    return send_from_directory('templates/assets/img', 'favicon.svg')

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
    # If HNS, redirect to HNS wallet
    if path == "HNS":
        # Get from 100.66.107.77:8080 then return result
        # Check for cookie
        if request.cookies.get('HNS'):
            return make_response(request.cookies.get('HNS'), 200, {'Content-Type': 'text/plain'})
        
        address = getAddress()
        # Set cookie
        resp = make_response(address, 200, {'Content-Type': 'text/plain'})
        # Cookie should last 1 week
        resp.set_cookie('HNS', address, max_age=604800)
        return resp

    return send_from_directory('.well-known/wallets', path, mimetype='text/plain')
        


# Main routes
@app.route('/')
def index():
    global address
    git=requests.get('https://git.woodburn.au/api/v1/users/nathanwoodburn/activities/feeds?only-performed-by=true&limit=1&token=' + os.getenv('git_token'))
    git = git.json()
    git = git[0]
    repo_name=git['repo']['name']
    repo_name=repo_name.lower()
    repo_description=git['repo']['description']
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
    
    

    if request.cookies.get('HNS'):
            return render_template('index.html', handshake_scripts=handshake_scripts, HNS=request.cookies.get('HNS'), repo=repo, repo_description=repo_description, custom=custom)
    
    if address == '':
        address = getAddress()
    # Set cookie
    resp = make_response(render_template('index.html', handshake_scripts=handshake_scripts, HNS=address, repo=repo, repo_description=repo_description, custom=custom), 200, {'Content-Type': 'text/html'})
    # Cookie should last 1 week
    resp.set_cookie('HNS', address, max_age=604800)
    return resp

@app.route('/now')
def now():
    
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true" or request.host == "test.nathan.woodburn.au":
        handshake_scripts = ""
    
    # Get latest now page
    files = os.listdir('templates/now')
    # Remove template
    files = [file for file in files if file != 'template.html']
    files.sort(reverse=True)
    return render_template('now/' + files[0], handshake_scripts=handshake_scripts)


@app.route('/<path:path>')
def catch_all(path):
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true" or request.host == "test.nathan.woodburn.au":
        handshake_scripts = ""
    # If file exists, load it
    if os.path.isfile('templates/' + path):
        return render_template(path, handshake_scripts=handshake_scripts)
    
    # Try with .html
    if os.path.isfile('templates/' + path + '.html'):
        return render_template(path + '.html', handshake_scripts=handshake_scripts)

    return render_template('404.html'), 404

def getAddress():
    global address
    if address == '':
        address = 'hs1qv3uu4amv87g7p7h49xez2pmzwjf92am0wzpnh4'
        # address = requests.get('http://hip02-server:3000').text?
    return address


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

    cf = CloudFlare.CloudFlare(token=os.getenv('CF_TOKEN'))
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



# 404 catch all
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')