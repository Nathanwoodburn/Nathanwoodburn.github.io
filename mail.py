import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from flask import jsonify
import os


def validateSender(email):
    domains = os.getenv("EMAIL_DOMAINS").split(",")
    for domain in domains:
        if re.match(r".+@" + domain, email):
            return True
        
    return False

def sendEmail(data):
    fromEmail = "noreply@woodburn.au"
    if "from" in data:
        fromEmail = data["from"]

    if not validateSender(fromEmail):
        return jsonify({
            "status": 400,
            "message": "Bad request 'from' email invalid"
        })


    if "to" not in data:
        return jsonify({
            "status": 400,
            "message": "Bad request 'to' json data missing"
        })
    to = data["to"]

    if "subject" not in data:
        return jsonify({
            "status": 400,
            "message": "Bad request 'subject' json data missing"
        })
    subject = data["subject"]

    if "body" not in data:
        return jsonify({
            "status": 400,
            "message": "Bad request 'body' json data missing"
        })
    body = data["body"]

    if not re.match(r"[^@]+@[^@]+\.[^@]+", to):
        raise ValueError("Invalid recipient email address.")
    
    if not subject:
        raise ValueError("Subject cannot be empty.")
    
    if not body:
        raise ValueError("Body cannot be empty.")
    
    fromName = "Nathan Woodburn"
    if 'sender' in data:
        fromName = data['sender']

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = formataddr((fromName, fromEmail))
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Sending the email
    try:
        with smtplib.SMTP_SSL(os.getenv("EMAIL_SMTP"), 465) as server:
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            server.sendmail(fromEmail, to, msg.as_string())
        print("Email sent successfully.")
        return jsonify({
            "status": 200,
            "message": "Send email successfully"
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "error": "Sending email failed",
            "exception":e
        })

    