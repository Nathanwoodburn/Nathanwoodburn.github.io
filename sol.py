from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solders.system_program import TransferParams, transfer
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.null_signer import NullSigner
import binascii
import base64
import os

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