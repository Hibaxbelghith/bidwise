"""
Branded HTML email templates for BidWise transactional emails.
All templates are inline-CSS for maximum email client compatibility.
"""


def otp_email_html(otp_code: str, expiry_minutes: int) -> str:
    """
    Professional OTP login code email.
    Returns an HTML string ready for EmailMessage(content_subtype='html').
    """
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Your BidWise Login Code</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:40px 0;">
    <tr>
      <td align="center">
        <!-- Container -->
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background-color:#2563eb;padding:32px 40px;text-align:center;">
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
                <tr>
                  <td style="background-color:rgba(255,255,255,0.15);border-radius:8px;padding:8px 10px;vertical-align:middle;">
                    <span style="color:#ffffff;font-size:20px;font-weight:700;">B</span>
                  </td>
                  <td style="padding-left:10px;vertical-align:middle;">
                    <span style="color:#ffffff;font-size:22px;font-weight:700;letter-spacing:-0.3px;">BidWise</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#171717;">
                Your login code
              </h1>
              <p style="margin:0 0 28px;font-size:15px;line-height:1.6;color:#525252;">
                Enter the code below to sign in to your BidWise account.
                This code expires in <strong>{expiry_minutes} minutes</strong>.
              </p>

              <!-- OTP Code -->
              <div style="background-color:#f5f5f5;border-radius:10px;padding:24px;text-align:center;margin-bottom:28px;">
                <span style="font-size:36px;font-weight:700;letter-spacing:8px;color:#171717;font-family:'Courier New',Courier,monospace;">
                  {otp_code}
                </span>
              </div>

              <p style="margin:0 0 4px;font-size:13px;line-height:1.5;color:#a3a3a3;">
                If you didn&#39;t request this code, you can safely ignore this email.
                Someone may have entered your email address by mistake.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="border-top:1px solid #f0f0f0;padding:24px 40px;text-align:center;">
              <p style="margin:0;font-size:12px;color:#a3a3a3;line-height:1.6;">
                &copy; 2026 BidWise &mdash; Smart Opportunity Matching<br />
                This is an automated message. Please do not reply.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def otp_email_plaintext(otp_code: str, expiry_minutes: int) -> str:
    """Plain-text fallback for email clients that don't render HTML."""
    return (
        f"Your BidWise login code\n"
        f"──────────────────────\n\n"
        f"Code: {otp_code}\n\n"
        f"This code expires in {expiry_minutes} minutes.\n"
        f"If you didn't request this code, please ignore this email.\n\n"
        f"— BidWise"
    )
