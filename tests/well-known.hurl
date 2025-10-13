GET http://127.0.0.1:5000/.well-known/xrp-ledger.toml
HTTP 200

GET http://127.0.0.1:5000/.well-known/nostr.json?name=hurl
HTTP 200
[Asserts]
jsonpath "$.names.hurl" == "b57b6a06fdf0a4095eba69eee26e2bf6fa72bd1ce6cbe9a6f72a7021c7acaa82"

GET http://127.0.0.1:5000/.well-known/wallets/BTC
HTTP 200

