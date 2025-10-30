from flask import Blueprint, request
import os
from cloudflare import Cloudflare
from tools import json_response

app = Blueprint('acme', __name__)


@app.route("/hnsdoh-acme", methods=["POST"])
def post():
    # Get the TXT record from the request
    if not request.is_json or not request.json:
        return json_response(request, "415 Unsupported Media Type", 415)
    if "txt" not in request.json or "auth" not in request.json:
        return json_response(request, "400 Bad Request", 400)

    txt = request.json["txt"]
    auth = request.json["auth"]
    if auth != os.getenv("CF_AUTH"):
        return json_response(request, "401 Unauthorized", 401)

    cf = Cloudflare(api_token=os.getenv("CF_TOKEN"))
    zone = cf.zones.list(name="hnsdoh.com").to_dict()
    zone_id = zone["result"][0]["id"]  # type: ignore
    existing_records = cf.dns.records.list(
        zone_id=zone_id, type="TXT", name="_acme-challenge.hnsdoh.com"  # type: ignore
    ).to_dict()
    record_id = existing_records["result"][0]["id"]  # type: ignore
    cf.dns.records.delete(dns_record_id=record_id, zone_id=zone_id)
    cf.dns.records.create(
        zone_id=zone_id,
        type="TXT",
        name="_acme-challenge",
        content=txt,
    )
    return json_response(request, "Success", 200)
