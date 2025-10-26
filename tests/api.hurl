GET http://127.0.0.1:5000/api/v1/
HTTP 200
GET http://127.0.0.1:5000/api/v1/help
HTTP 200
GET http://127.0.0.1:5000/api/v1/ip
HTTP 200
[Asserts]
jsonpath "$.ip" == "127.0.0.1"
GET http://127.0.0.1:5000/api/v1/time
HTTP 200
GET http://127.0.0.1:5000/api/v1/timezone
HTTP 200
GET http://127.0.0.1:5000/api/v1/message
HTTP 200
GET http://127.0.0.1:5000/api/v1/project
HTTP 200
GET http://127.0.0.1:5000/api/v1/tools
HTTP 200
[Asserts]
jsonpath "$.tools" count > 5