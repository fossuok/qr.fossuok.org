import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
MAILJET_API_SECRET = os.getenv("MAILJET_API_SECRET")
MAILJET_SENDER_EMAIL = os.getenv("MAILJET_SENDER_EMAIL")
MAILJET_SENDER_NAME = os.getenv("MAILJET_SENDER_NAME", "QR Event")

_MAILJET_URL = "https://api.mailjet.com/v3.1/send"


async def send_qr_email(
    email: str,
    name: str,
    qr_data_url: str,
    client: Optional[httpx.AsyncClient] = None,
) -> None:
    """
    Sends an email with the QR code using MailJet API v3.1.

    Pass a shared ``httpx.AsyncClient`` (from ``app.state.http_client``) to
    avoid creating a new TCP connection for every email.  If no client is
    provided a temporary one is created — useful for scripts and tests.
    """
    if not MAILJET_API_KEY or not MAILJET_API_SECRET:
        print("MailJet credentials missing. Skipping email.")
        return

    payload = {
        "Messages": [
            {
                "From": {
                    "Email": MAILJET_SENDER_EMAIL,
                    "Name": MAILJET_SENDER_NAME,
                },
                "To": [{"Email": email, "Name": name}],
                "Subject": f"Your QR Code for {MAILJET_SENDER_NAME}",
                "HTMLPart": (
                    f"<h3>Hi {name},</h3>"
                    f"<p>Thank you for registering! Here is your QR code:</p>"
                    f"<img src='{qr_data_url}' alt='QR Code' />"
                    f"<p>Show this at the entrance.</p>"
                ),
            }
        ]
    }

    if client is not None:
        response = await client.post(
            _MAILJET_URL,
            auth=(MAILJET_API_KEY, MAILJET_API_SECRET),
            json=payload,
        )
        response.raise_for_status()
    else:
        async with httpx.AsyncClient() as _client:
            response = await _client.post(
                _MAILJET_URL,
                auth=(MAILJET_API_KEY, MAILJET_API_SECRET),
                json=payload,
            )
            response.raise_for_status()
