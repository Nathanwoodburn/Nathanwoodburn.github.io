from flask import Flask, make_response, redirect, request, jsonify, render_template, send_from_directory
import os
import dotenv

app = Flask(__name__)
dotenv.load_dotenv()

@app.route('/assets/<path:path>')
def send_report(path):
    return send_from_directory('templates/assets', path)


@app.route('/')
def index():
    handshake_scripts = "<script src=\"https://nathan.woodburn/handshake.js\" domain=\"nathan.woodburn\"></script><script src=\"https://nathan.woodburn/https.js\"></script>"
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000":
        handshake_scripts = ""
    return render_template('index.html', handshake_scripts=handshake_scripts)

@app.route('/<path:path>')
def catch_all(path):
    handshake_scripts = "<script src=\"https://nathan.woodburn/handshake.js\" domain=\"nathan.woodburn\"></script><script src=\"https://nathan.woodburn/https.js\"></script>"
    # If localhost, don't load handshake
    if request.host == "localhost:5000" or request.host == "127.0.0.1:5000":
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