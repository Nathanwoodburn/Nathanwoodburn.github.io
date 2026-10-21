GET http://127.0.0.1:5000/.well-known/xrp-ledger.toml
HTTP 200

GET http://127.0.0.1:5000/.well-known/nostr.json?name=hurl
HTTP 200
[Asserts]
jsonpath "$.names.hurl" == "b57b6a06fdf0a4095eba69eee26e2bf6fa72bd1ce6cbe9a6f72a7021c7acaa82"

GET http://127.0.0.1:5000/.well-known/wallets/BTC
HTTP 200

GET http://127.0.0.1:5000/sitemap.xml
HTTP 200
[Asserts]
header "Content-Type" contains "application/xml"
body contains "https://nathan.woodburn.au</loc>"
body contains "https://nathan.woodburn.au/blog</loc>"
body contains "https://nathan.woodburn.au/tools</loc>"

GET http://127.0.0.1:5000/robots.txt
HTTP 200
[Asserts]
header "Content-Type" contains "text/plain"
body contains "Sitemap: https://nathan.woodburn.au/sitemap.xml"

GET http://127.0.0.1:5000/.well-known/security.txt
HTTP 200
[Asserts]
body contains "BEGIN PGP SIGNED MESSAGE"
body contains "contact@nathan.woodburn.au"

GET http://127.0.0.1:5000/security.txt
HTTP 302
[Asserts]
header "Location" contains "/.well-known/security.txt"

