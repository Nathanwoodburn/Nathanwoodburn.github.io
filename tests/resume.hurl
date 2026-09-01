GET http://127.0.0.1:5000/resume
HTTP 200

GET http://127.0.0.1:5000/resume.json
HTTP 200
[Asserts]
jsonpath "$.name" == "Nathan Woodburn"
jsonpath "$.active_title" == "Linux Systems Administrator"

GET http://127.0.0.1:5000/resume.json?support=1
HTTP 200
[Asserts]
jsonpath "$.name" == "Nathan Woodburn"
jsonpath "$.active_title" == "Technical Support Specialist"

GET http://127.0.0.1:5000/resume.md
HTTP 200
[Asserts]
body contains "# Nathan Woodburn"
body contains "Linux Systems Administrator"

GET http://127.0.0.1:5000/resume.md?support=1
HTTP 200
[Asserts]
body contains "# Nathan Woodburn"
body contains "Technical Support Specialist"

GET http://127.0.0.1:5000/resume.txt
HTTP 200
[Asserts]
body contains "NATHAN WOODBURN"
body contains "Linux Systems Administrator"

GET http://127.0.0.1:5000/resume.txt?support=1
HTTP 200
[Asserts]
body contains "NATHAN WOODBURN"
body contains "Technical Support Specialist"

GET http://127.0.0.1:5000/resume.ascii
HTTP 200
[Asserts]
body contains "RESUME: NATHAN WOODBURN"
body contains "Linux Systems Administrator"

GET http://127.0.0.1:5000/resume.pdf
HTTP 200

GET http://127.0.0.1:5000/resume.pdf?support=1
HTTP 200
