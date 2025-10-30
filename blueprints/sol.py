from flask import Blueprint, request, jsonify, make_response
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solders.system_program import TransferParams, transfer
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.null_signer import NullSigner
import binascii
import base64
import os

app = Blueprint('sol', __name__)

SOLANA_HEADERS = {
    "Content-Type": "application/json",
    "X-Action-Version": "2.4.2",
    "X-Blockchain-Ids": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
}

SOLANA_ADDRESS = None
if os.path.isfile(".well-known/wallets/SOL"):
    with open(".well-known/wallets/SOL") as file:
        address = file.read()
    SOLANA_ADDRESS = Pubkey.from_string(address.strip())

def create_transaction(sender_address: str, amount: float) -> str:
    if SOLANA_ADDRESS is None:
        raise ValueError("SOLANA_ADDRESS is not set. Please ensure the .well-known/wallets/SOL file exists and contains a valid address.")
    # Create transaction
    sender = Pubkey.from_string(sender_address)
    transfer_ix = transfer(
        TransferParams(
            from_pubkey=sender, to_pubkey=SOLANA_ADDRESS, lamports=int(
                amount * 1000000000)
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
    return base64_string

def get_solana_address() -> str:
    if SOLANA_ADDRESS is None:
        raise ValueError("SOLANA_ADDRESS is not set. Please ensure the .well-known/wallets/SOL file exists and contains a valid address.")
    return str(SOLANA_ADDRESS) 

@app.route("/donate", methods=["GET", "OPTIONS"])
def sol_donate():
    data = {
        "icon": "https://nathan.woodburn.au/assets/img/profile.png",
        "label": "Donate to Nathan.Woodburn/",
        "title": "Donate to Nathan.Woodburn/",
        "description": "Student, developer, and crypto enthusiast",
        "links": {
            "actions": [
                {"label": "0.01 SOL", "href": "/api/v1/donate/0.01"},
                {"label": "0.1 SOL", "href": "/api/v1/donate/0.1"},
                {"label": "1 SOL", "href": "/api/v1/donate/1"},
                {
                    "href": "/api/v1/donate/{amount}",
                    "label": "Donate",
                    "parameters": [
                        {"name": "amount", "label": "Enter a custom SOL amount"}
                    ],
                },
            ]
        },
    }

    response = make_response(jsonify(data), 200, SOLANA_HEADERS)

    if request.method == "OPTIONS":
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type,Authorization,Content-Encoding,Accept-Encoding,X-Action-Version,X-Blockchain-Ids"
        )

    return response


@app.route("/donate/<amount>")
def sol_donate_amount(amount):
    data = {
        "icon": "https://nathan.woodburn.au/assets/img/profile.png",
        "label": f"Donate {amount} SOL to Nathan.Woodburn/",
        "title": "Donate to Nathan.Woodburn/",
        "description": f"Donate {amount} SOL to Nathan.Woodburn/",
    }
    return jsonify(data), 200, SOLANA_HEADERS


@app.route("/donate/<amount>", methods=["POST"])
def sol_donate_post(amount):

    if not request.json:
        return jsonify({"message": "Error: No JSON data provided"}), 400, SOLANA_HEADERS

    if "account" not in request.json:
        return jsonify({"message": "Error: No account provided"}), 400, SOLANA_HEADERS

    sender = request.json["account"]

    # Make sure amount is a number
    try:
        amount = float(amount)
    except ValueError:
        amount = 1  # Default to 1 SOL if invalid

    if amount < 0.0001:
        return jsonify({"message": "Error: Amount too small"}), 400, SOLANA_HEADERS

    transaction = create_transaction(sender, amount)
    return jsonify({"message": "Success", "transaction": transaction}), 200, SOLANA_HEADERS