import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# CHANGE THESE
SENDER_EMAIL = "anirudhvsbagya@gmail.com"
APP_PASSWORD = "wgzmoayfxerllbna"

def send_reminder_email(to_email, user_name, spent, budget):
    exceeded_by = spent - budget

    subject = "⚠️ Monthly Budget Exceeded"

    body = f"""
Hello {user_name},

This is an automatic alert from your Finance Tracker.

🚨 Budget Exceeded!

• Monthly Budget: ₹{budget}
• Total Spent: ₹{spent}
• Exceeded By: ₹{exceeded_by}

Please review your expenses and plan accordingly.

— Finance Tracker System
"""

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Budget alert email sent successfully")

    except Exception as e:
        print("Email sending failed:", e)
