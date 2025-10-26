from flask import Blueprint, request
from tools import json_response

template_bp = Blueprint('template', __name__)


@template_bp.route("/")
def index():
    return json_response(request, "Success", 200)