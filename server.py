from flask import Flask, make_response, redirect, request, jsonify, render_template, send_from_directory
import os
import dotenv

app = Flask(__name__)
dotenv.load_dotenv()

# Custom header
def add_custom_header(response):
    response.headers['Onion-Location'] = 'http://wdbrncwefot4hd7bdrz5rzb74mefay7zvrjn2vmkpdm44l7fwnih5ryd.onion/'
    return response
app.after_request(add_custom_header)


#Assets routes
@app.route('/assets/<path:path>')
def send_report(path):
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


# Main routes

@app.route('/')
def index():
    handshake_scripts = "<script src=\"https://nathan.woodburn/handshake.js\" domain=\"nathan.woodburn\"></script><script src=\"https://nathan.woodburn/https.js\"></script>"
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true":
        handshake_scripts = ""
    return render_template('index.html', handshake_scripts=handshake_scripts)


@app.route('/<path:path>')
def catch_all(path):
    handshake_scripts = "<script src=\"https://nathan.woodburn/handshake.js\" domain=\"nathan.woodburn\"></script><script src=\"https://nathan.woodburn/https.js\"></script>"
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000" or os.getenv('dev') == "true":
        handshake_scripts = ""
    # If file exists, load it
    if os.path.isfile('templates/' + path):
        return render_template(path, handshake_scripts=handshake_scripts)
    
    # Try with .html
    if os.path.isfile('templates/' + path + '.html'):
        return render_template(path + '.html', handshake_scripts=handshake_scripts)

    return render_template('404.html'), 404

# 404 catch all
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=False, port=5000, host='0.0.0.0')