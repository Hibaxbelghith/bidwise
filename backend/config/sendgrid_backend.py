"""
Custom Django email backend using SendGrid Web API v3.

Uses HTTP POST to https://api.sendgrid.com/v3/mail/send instead of SMTP.
This avoids all SMTP port/TLS/firewall issues inside Docker containers.

Django's send_mail() and EmailMessage work unchanged — this backend
is a drop-in replacement for django.core.mail.backends.smtp.EmailBackend.
"""

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


SENDGRID_API_URL = 'https://api.sendgrid.com/v3/mail/send'


class SendGridAPIBackend(BaseEmailBackend):
    """
    Send emails via SendGrid Web API v3.

    Required settings:
        SENDGRID_API_KEY   — SendGrid API key with Mail Send permission
        DEFAULT_FROM_EMAIL — Verified sender address
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, 'SENDGRID_API_KEY', '')

    def send_messages(self, email_messages):
        if not self.api_key:
            if not self.fail_silently:
                raise ValueError('SENDGRID_API_KEY is not configured.')
            return 0

        sent = 0
        for message in email_messages:
            try:
                if self._send(message):
                    sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message):
        """Send a single EmailMessage via the SendGrid API."""
        if not message.recipients():
            return False

        from_email = message.from_email or settings.DEFAULT_FROM_EMAIL

        payload = {
            'personalizations': [
                {
                    'to': [{'email': addr} for addr in message.to],
                }
            ],
            'from': {'email': from_email},
            'subject': message.subject,
            'content': [
                {
                    'type': 'text/html' if message.content_subtype == 'html' else 'text/plain',
                    'value': message.body,
                }
            ],
        }

        # Add CC if present
        if message.cc:
            payload['personalizations'][0]['cc'] = [{'email': addr} for addr in message.cc]

        # Add BCC if present
        if message.bcc:
            payload['personalizations'][0]['bcc'] = [{'email': addr} for addr in message.bcc]

        # Add Reply-To if present
        if message.reply_to:
            payload['reply_to'] = {'email': message.reply_to[0]}

        response = requests.post(
            SENDGRID_API_URL,
            json=payload,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            timeout=10,
        )

        # 2xx = success (202 Accepted is the normal response)
        if response.status_code >= 400:
            error_detail = response.text
            if not self.fail_silently:
                raise Exception(
                    f'SendGrid API error {response.status_code}: {error_detail}'
                )
            return False

        return True
