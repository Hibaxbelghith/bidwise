from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from django.conf import settings


@dataclass(frozen=True)
class OrganizationDecisionEmail:
    subject: str
    plaintext: str
    html: str


def _clean_header(value):
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


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
                            padding:12px 18px;border-radius:6px;font-weight:700;">
                    {action_label}
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


def build_admin_approved_email(opportunity):
    title = _clean_header(opportunity.titre)
    public_url = _frontend_url(f"opportunities/{opportunity.pk}")
    subject = f"Your opportunity is now published - {title}"
    plaintext = (
        f'Your opportunity "{title}" has been reviewed and approved by our team.\n'
        "It is now visible to candidates.\n\n"
        f"View your opportunity: {public_url}"
    )
    body_html = (
        f'<p>Your opportunity <strong>"{escape(title)}"</strong> has been reviewed '
        "and approved by our team.</p>"
        "<p>It is now visible to candidates.</p>"
    )
    return OrganizationDecisionEmail(
        subject=subject,
        plaintext=plaintext,
        html=_email_shell(
            heading="Your opportunity is now published",
            body_html=body_html,
            action_label="View my opportunity",
            action_url=public_url,
        ),
    )


def build_automatic_approved_email(opportunity):
    title = _clean_header(opportunity.titre)
    public_url = _frontend_url(f"opportunities/{opportunity.pk}")
    subject = f"Your opportunity is now published - {title}"
    plaintext = (
        f'Your opportunity "{title}" has passed our publication checks.\n'
        "It is now published and visible to candidates.\n\n"
        f"View your opportunity: {public_url}"
    )
    body_html = (
        f'<p>Your opportunity <strong>"{escape(title)}"</strong> has passed '
        "our publication checks.</p>"
        "<p>It is now published and visible to candidates.</p>"
    )
    return OrganizationDecisionEmail(
        subject=subject,
        plaintext=plaintext,
        html=_email_shell(
            heading="Your opportunity is now published",
            body_html=body_html,
            action_label="View my opportunity",
            action_url=public_url,
        ),
    )


def build_admin_rejected_email(opportunity, *, admin_note=""):
    title = _clean_header(opportunity.titre)
    note = str(admin_note or "").strip()
    public_reason = note or "It does not meet our publication criteria."
    support_email = str(
        getattr(settings, "BIDWISE_SUPPORT_EMAIL", "support@bidwise.com")
    ).strip()
    support_url = f"mailto:{quote(support_email, safe='@')}"
    subject = f"Your opportunity could not be published - {title}"
    plaintext = (
        f'Your opportunity "{title}" has been reviewed and was not accepted '
        "for publication on BidWise.\n\n"
        f"{public_reason}\n\n"
        f"If you have questions, contact our support: {support_email}"
    )
    body_html = (
        f'<p>Your opportunity <strong>"{escape(title)}"</strong> has been reviewed '
        "and was not accepted for publication on BidWise.</p>"
        f'<p style="padding:12px;background:#fafafa;border-left:3px solid #dc2626;">'
        f"{escape(public_reason)}</p>"
        "<p>If you have questions, contact our support.</p>"
    )
    return OrganizationDecisionEmail(
        subject=subject,
        plaintext=plaintext,
        html=_email_shell(
            heading="Your opportunity could not be published",
            body_html=body_html,
            action_label="Contact support",
            action_url=support_url,
        ),
    )


def build_new_application_email(candidature):
    """Build email notification for new application submitted to organization."""
    # Extract candidate name from profil if available, fallback to first/last name, then email
    candidate_name = ""
    if hasattr(candidature.candidat, "profil"):
        prenom = getattr(candidature.candidat.profil, "prenom", "").strip()
        nom = getattr(candidature.candidat.profil, "nom", "").strip()
        candidate_name = _clean_header(f"{prenom} {nom}".strip())
    
    if not candidate_name:
        candidate_name = _clean_header(
            f"{candidature.candidat.first_name} {candidature.candidat.last_name}".strip()
        )
    
    if not candidate_name:
        candidate_name = candidature.candidat.email
    
    opportunity_title = _clean_header(candidature.opportunite.titre)
    dashboard_url = _frontend_url("organization/dashboard")
    
    subject = f"New application — {opportunity_title}"
    
    phone_line = f"Phone   : {candidature.contact_phone}\n" if candidature.contact_phone else ""
    plaintext = (
        f'{candidate_name} applied for "{opportunity_title}".\n\n'
        f"Email   : {candidature.contact_email}\n"
        f"{phone_line}\n"
        f"View applications: {dashboard_url}"
    )
    
    phone_html = f"<p><strong>Phone:</strong> {escape(candidature.contact_phone)}</p>" if candidature.contact_phone else ""
    body_html = (
        f'<p><strong>{escape(candidate_name)}</strong> applied for '
        f'<strong>"{escape(opportunity_title)}"</strong>.</p>'
        f"<p><strong>Email:</strong> {escape(candidature.contact_email)}</p>"
        f"{phone_html}"
    )
    
    return OrganizationDecisionEmail(
        subject=subject,
        plaintext=plaintext,
        html=_email_shell(
            heading="New application received",
            body_html=body_html,
            action_label="View applications",
            action_url=dashboard_url,
        ),
    )


def build_candidate_application_submitted_email(candidature):
    title = _clean_header(candidature.opportunite.titre)
    organization_name = _clean_header(
        getattr(candidature.opportunite, "organisation_nom", "")
        or getattr(candidature.opportunite.organisation, "company_name", "")
        or getattr(candidature.opportunite.organisation, "email", "")
    )
    dashboard_url = _frontend_url("dashboard")

    subject = f"Application submitted - {title}"
    plaintext = (
        f'Your application for "{title}" has been submitted successfully.\n'
        f"Organization: {organization_name or 'BidWise organization'}\n\n"
        "You can track this application from your BidWise dashboard.\n\n"
        f"View my applications: {dashboard_url}"
    )
    body_html = (
        f'<p>Your application for <strong>"{escape(title)}"</strong> has been '
        "submitted successfully.</p>"
        f"<p><strong>Organization:</strong> {escape(organization_name or 'BidWise organization')}</p>"
        "<p>You can track this application from your BidWise dashboard.</p>"
    )
    return OrganizationDecisionEmail(
        subject=subject,
        plaintext=plaintext,
        html=_email_shell(
            heading="Your application has been submitted",
            body_html=body_html,
            action_label="View my applications",
            action_url=dashboard_url,
        ),
    )
