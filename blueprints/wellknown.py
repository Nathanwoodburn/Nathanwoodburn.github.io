from flask import Blueprint, make_response, request, jsonify, send_from_directory, redirect
from tools import error_response
import os

app = Blueprint('well-known', __name__, url_prefix='/.well-known')


@app.route("/<path:path>")
def index(path):
    return send_from_directory(".well-known", path)


@app.route("/wallets/<path:path>")
def wallets(path):
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

    return error_response(request)


@app.route("/nostr.json")
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


@app.route("/xrp-ledger.toml")
def xrp():
    # Create a response with the xrp-ledger.toml file
    with open(".well-known/xrp-ledger.toml") as file:
        toml = file.read()

    response = make_response(toml, 200, {"Content-Type": "application/toml"})
    # Set cors headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response
