from flask import Flask, render_template, request
import smtplib
from email.message import EmailMessage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import urllib.parse, uuid  # unique token generate করার জন্য uuid

app = Flask(__name__)

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Form Responses").sheet1

# --- Brevo SMTP Setup ---
BREVO_SMTP_SERVER = "smtp-relay.brevo.com"
BREVO_SMTP_PORT = 587
BREVO_USERNAME = "9ba143001@smtp-brevo.com"   # Your Brevo login username
BREVO_PASSWORD = "xsmtpsib-51a64dc99f512c49c79dda57ae1fe088c96181b79b60cfdea5cbe03b0ee0a5a4-HjPOVzQl42bPJjep"        # Replace with Brevo SMTP key
FROM_EMAIL = "barammanik@gmail.com"          # Must be a verified Brevo sender email


@app.route("/")
def index():
    return render_template("form.html")


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form["name"]
    email = request.form["email"]

    # ইউনিক একবার ব্যবহারযোগ্য টোকেন তৈরি
    token = str(uuid.uuid4())
    verify_url = request.host_url.rstrip("/") + "/verify?" + urllib.parse.urlencode({"token": token})

    # verify_email.html থেকে HTML কন্টেন্ট নেওয়া
    html_content = render_template("verify_email.html", name=name, verify_url=verify_url)

    msg = EmailMessage()
    msg["Subject"] = "Verify your form submission"
    msg["From"] = FROM_EMAIL
    msg["To"] = email
    msg.add_alternative(html_content, subtype="html")

    # ---------- Brevo SMTP ----------
    with smtplib.SMTP(BREVO_SMTP_SERVER, BREVO_SMTP_PORT) as smtp:
        smtp.starttls()  # TLS start (VERY IMPORTANT)
        smtp.login(BREVO_USERNAME, BREVO_PASSWORD)
        smtp.send_message(msg)

    # Google Sheet-এ ডেটা যোগ করা
    sheet.append_row([name, email, token, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

    return render_template("sucess.html")


@app.route("/verify")
def verify():
    token = request.args.get("token")

    records = sheet.get_all_records()
    for i, record in enumerate(records, start=2):  # start=2 কারণ Row 1 হলো header
        if record["Token"] == token and record["Verified"] == "Pending":
            sheet.update_cell(i, 4, "Verified")  # Column D = Verified
            return f"<h2>✅ Verification Successful for {record['Name']} ({record['Email']})!</h2>"

    return "<h2>❌ Invalid or already verified link!</h2>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
