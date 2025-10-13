
GET http://127.0.0.1:5000/api/help
HTTP 301
[Asserts]
header "Location" == "/api/v1/help"

GET http://127.0.0.1:5000/api/ip
HTTP 301
[Asserts]
header "Location" == "/api/v1/ip"

GET http://127.0.0.1:5000/api/message
HTTP 301
[Asserts]
header "Location" == "/api/v1/message"

GET http://127.0.0.1:5000/api/project
HTTP 301
[Asserts]
header "Location" == "/api/v1/project"

GET http://127.0.0.1:5000/api/donate
HTTP 301
[Asserts]
header "Location" == "/api/v1/donate"

GET http://127.0.0.1:5000/api/time
HTTP 301
[Asserts]
header "Location" == "/api/v1/time"

GET http://127.0.0.1:5000/api/timezone
HTTP 301
[Asserts]
header "Location" == "/api/v1/timezone"

GET http://127.0.0.1:5000/api/version
HTTP 301
[Asserts]
header "Location" == "/api/v1/version"

