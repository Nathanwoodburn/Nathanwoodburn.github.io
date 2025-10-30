from flask import Blueprint, request
from tools import json_response

app = Blueprint('template', __name__)


@app.route("/")
def index():
    return json_response(request, "Success", 200)