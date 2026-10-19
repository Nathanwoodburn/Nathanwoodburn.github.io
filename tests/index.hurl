GET http://127.0.0.1:5000/
HTTP 200

GET http://127.0.0.1:5000/assets/bootstrap/css/bootstrap.min.css
HTTP 200

GET http://127.0.0.1:5000/assets/css/styles.min.css
HTTP 200

GET http://127.0.0.1:5000/favicon.png
HTTP 200

GET http://127.0.0.1:5000/assets/spotify.webp
HTTP 200

GET http://127.0.0.1:5000/assets/spotify.png
HTTP 200

GET http://127.0.0.1:5000/assets/background.webp
HTTP 200

GET http://127.0.0.1:5000/assets/nathan3dprinting.webp
HTTP 200

GET http://127.0.0.1:5000/about
HTTP 200
[Asserts]
header "Cache-Control" == "no-cache, must-revalidate"
header "ETag" exists
xpath "//a[contains(@class, 'about-slideout-link')]" exists
xpath "//svg[contains(@class, 'about-slideout-btn')]" exists

GET http://127.0.0.1:5000/assets/css/about.css
HTTP 200
[Asserts]
header "Cache-Control" == "public, no-cache, must-revalidate"

GET http://127.0.0.1:5000/assets/css/about.css?v=test12345
HTTP 200
[Asserts]
header "Cache-Control" == "public, max-age=31536000, immutable"