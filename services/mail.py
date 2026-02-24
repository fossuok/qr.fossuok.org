import os

import httpx
from dotenv import load_dotenv

load_dotenv()

MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
MAILJET_API_SECRET = os.getenv("MAILJET_API_SECRET")
MAILJET_SENDER_EMAIL = os.getenv("MAILJET_SENDER_EMAIL")
MAILJET_SENDER_NAME = os.getenv("MAILJET_SENDER_NAME", "QR Event")


async def send_qr_email(email: str, name: str, qr_data_url: str):
    """Sends an email with the QR code using MailJet API v3.1."""
    if not MAILJET_API_KEY or not MAILJET_API_SECRET:
        print("MailJet credentials missing. Skipping email.")
        return

    url = "https://api.mailjet.com/v3.1/send"

    # MailJet expects base64 data without the prefix for attachments, 
    # but we can also just embed it in the HTML.
    # For now, let's embed it in the HTML as a data URL or send as attachment.
    # Data URL in HTML is easier for most clients.

    payload = {
        "Messages": [
            {
                "From": {
                    "Email": MAILJET_SENDER_EMAIL,
                    "Name": MAILJET_SENDER_NAME
                },
                "To": [
                    {
                        "Email": email,
                        "Name": name
                    }
                ],
                "Subject": f"Your QR Code for {MAILJET_SENDER_NAME}",
                "HTMLPart": f"<h3>Hi {name},</h3><p>Thank you for registering! Here is your QR code:</p><img src='{qr_data_url}' alt='QR Code' /><p>Show this at the entrance.</p>"
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            auth=(MAILJET_API_KEY, MAILJET_API_SECRET),
            json=payload
        )
        response.raise_for_status()
        return response.json()
