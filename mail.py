import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from flask import jsonify
import os


# This is used to send emails via API
# The process should be something like this
# curl --request POST \
#   --url https://nathan.c.woodburn.au/api/email \
#   --header 'Content-Type: application/json' \
#   --data '{
#         "key":"api-key",
#         "to": "recipient@nathan.woodburn.au",
#         "from": "sender@nathan.woodburn.au",
#         "sender":"Nathan.Woodburn/",
#         "subject":"Test email from api",
#         "body":"G'\''day\nThis is a test email from my website api\n\nRegards,\nNathan.Woodburn/"
# }'


def validateSender(email):
    domains = os.getenv("EMAIL_DOMAINS")
    if not domains:
        return False

    domains = domains.split(",")
    for domain in domains:
        if re.match(r".+@" + domain, email):
            return True

    return False


def sendEmail(data):
    fromEmail = "noreply@woodburn.au"
    if "from" in data:
        fromEmail = data["from"]

    if not validateSender(fromEmail):
        return jsonify({"status": 400, "message": "Bad request 'from' email invalid"})

    if "to" not in data:
        return jsonify({"status": 400, "message": "Bad request 'to' json data missing"})
    to = data["to"]

    if "subject" not in data:
        return jsonify(
            {"status": 400, "message": "Bad request 'subject' json data missing"}
        )
    subject = data["subject"]

    if "body" not in data:
        return jsonify(
            {"status": 400, "message": "Bad request 'body' json data missing"}
        )
    body = data["body"]

    if not re.match(r"[^@]+@[^@]+\.[^@]+", to):
        raise ValueError("Invalid recipient email address.")

    if not subject:
        raise ValueError("Subject cannot be empty.")

    if not body:
        raise ValueError("Body cannot be empty.")

    fromName = "Nathan Woodburn"
    if "sender" in data:
        fromName = data["sender"]

    # Create the email message
    msg = MIMEMultipart()
    msg["From"] = formataddr((fromName, fromEmail))
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Sending the email
    try:
        host = os.getenv("EMAIL_SMTP")
        user = os.getenv("EMAIL_USER")
        password = os.getenv("EMAIL_PASS")
        if host is None or user is None or password is None:
            return jsonify({"status": 500, "error": "Email server not configured"})

        with smtplib.SMTP_SSL(host, 465) as server:
            server.login(user, password)
            server.sendmail(fromEmail, to, msg.as_string())
        print("Email sent successfully.")
        return jsonify({"status": 200, "message": "Send email successfully"})
    except Exception as e:
        return jsonify({"status": 500, "error": "Sending email failed", "exception": e})
