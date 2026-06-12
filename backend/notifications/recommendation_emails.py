from dataclasses import dataclass
from html import escape

from django.conf import settings


@dataclass(frozen=True)
class RecommendationDigestEmail:
    subject: str
    plaintext: str
    html: str


def _frontend_url(path):
    base_url = str(
        getattr(settings, "BIDWISE_FRONTEND_URL", "http://localhost:5173")
    ).strip().rstrip("/")
    return f"{base_url}/{str(path).lstrip('/')}"


def _email_shell(*, heading, body_html, action_label, action_url):
    return f"""\
<!doctype html>
<html lang="en">
  <body style="margin:0;background:#f5f5f4;font-family:Arial,sans-serif;color:#171717;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                 style="max-width:600px;background:#ffffff;border:1px solid #e5e5e5;border-radius:8px;">
            <tr>
              <td style="padding:32px;">
                <p style="margin:0 0 24px;color:#1d4ed8;font-size:20px;font-weight:700;">BidWise</p>
                <h1 style="margin:0 0 20px;font-size:24px;line-height:1.35;">{heading}</h1>
                <div style="font-size:15px;line-height:1.7;color:#404040;">{body_html}</div>
                <p style="margin:28px 0 0;">
                  <a href="{escape(action_url, quote=True)}"
                     style="display:inline-block;background:#1d4ed8;color:#ffffff;text-decoration:none;
                            padding:12px 18px;border-radius:8px;font-weight:600;">
                    {escape(action_label)}
                  </a>
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def build_recommendation_digest_email(*, first_name, opportunities):
    safe_first_name = str(first_name or "").strip() or "there"
    browse_url = _frontend_url("opportunities")
    subject = "New opportunities matching your profile"

    plaintext_items = []
    html_items = []
    for item in opportunities:
        title = str(item.get("title") or item.get("titre") or "Opportunity").strip()
        company = str(item.get("company") or item.get("organisation_nom") or "Organization").strip()
        location = str(item.get("location") or item.get("ville") or "Not specified").strip()
        plaintext_items.append(f"- {title} | {company} | {location}")
        html_items.append(
            f"<li><strong>{escape(title)}</strong><br>"
            f"{escape(company)} · {escape(location)}</li>"
        )

    plaintext = (
        f"Hello {safe_first_name},\n\n"
        "Here are new opportunities matching your profile:\n\n"
        + "\n".join(plaintext_items)
        + f"\n\nView opportunities: {browse_url}"
    )
    body_html = (
        f"<p>Hello {escape(safe_first_name)},</p>"
        "<p>Here are new opportunities matching your profile:</p>"
        f"<ul style=\"padding-left:20px;margin:16px 0;\">{''.join(html_items)}</ul>"
    )
    return RecommendationDigestEmail(
        subject=subject,
        plaintext=plaintext,
        html=_email_shell(
            heading="New opportunities matching your profile",
            body_html=body_html,
            action_label="View opportunities",
            action_url=browse_url,
        ),
    )
