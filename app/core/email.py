"""Synchronous email helpers using Flask-Mail.

For async sending, use the Celery tasks in core/tasks.py.
"""

from flask import current_app
from flask_mail import Message

from app.extensions import mail


# ── Brand constants ────────────────────────────────────────────────────
_BRAND_GREEN = "#17341d"
_BRAND_GREEN_LIGHT = "#2d4b32"
_BRAND_ORANGE = "#fe932c"
_BRAND_SURFACE = "#fcf9f8"
_BRAND_TEXT = "#1b1c1c"
_BRAND_MUTED = "#6b6b6b"


def _base_html(content: str, preheader: str = "", unsubscribe_url: str = "") -> str:
    """Wrap email content in the branded HTML shell."""
    unsub_html = ""
    if unsubscribe_url:
        unsub_html = f"""\
  <p style="margin:8px 0 0;font-size:11px;color:{_BRAND_MUTED};">
    <a href="{unsubscribe_url}" style="color:{_BRAND_MUTED};text-decoration:underline;">Unsubscribe</a>
    &nbsp;&middot;&nbsp;
    <a href="https://bookwithsheilla.com/data-rights" style="color:{_BRAND_MUTED};text-decoration:underline;">Data Rights</a>
  </p>"""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Book With Sheilla</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#f0edec;font-family:'Plus Jakarta Sans',Helvetica,Arial,sans-serif;">
<span style="display:none;font-size:1px;color:#f0edec;max-height:0;overflow:hidden;">{preheader}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0edec;">
<tr><td align="center" style="padding:40px 16px;">

<!-- Container -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background-color:{_BRAND_SURFACE};border-radius:12px;overflow:hidden;">

<!-- Header -->
<tr>
<td style="background:linear-gradient(135deg,{_BRAND_GREEN},{_BRAND_GREEN_LIGHT});padding:32px 40px;text-align:center;">
  <h1 style="margin:0;font-family:'Noto Serif',Georgia,serif;font-size:24px;font-weight:700;color:#ffffff;letter-spacing:0.5px;">
    Book With Sheilla
  </h1>
  <p style="margin:6px 0 0;font-size:12px;color:rgba(255,255,255,0.75);letter-spacing:1.5px;text-transform:uppercase;">
    Curated Safari &amp; Tour Experiences
  </p>
</td>
</tr>

<!-- Body -->
<tr>
<td style="padding:36px 40px 28px;">
{content}
</td>
</tr>

<!-- Footer -->
<tr>
<td style="padding:20px 40px 32px;border-top:1px solid #e4e2e1;text-align:center;">
  <p style="margin:0 0 8px;font-size:12px;color:{_BRAND_MUTED};">
    Book With Sheilla &middot; Curated Safari &amp; Tour Experiences
  </p>
  <p style="margin:0;font-size:11px;color:{_BRAND_MUTED};">
    <a href="https://bookwithsheilla.com" style="color:{_BRAND_GREEN_LIGHT};text-decoration:none;">bookwithsheilla.com</a>
  </p>
{unsub_html}
</td>
</tr>

</table>
<!-- /Container -->

</td></tr>
</table>
</body>
</html>"""


def send_email(
    to: str,
    subject: str,
    body: str,
    html: str = None,
    attachments: list = None,
    unsubscribe_url: str = None,
):
    """Send an email synchronously."""
    msg = Message(
        subject=subject,
        recipients=[to],
        body=body,
        html=html,
        sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
        reply_to=current_app.config.get("MAIL_REPLY_TO") or None,
    )
    if unsubscribe_url:
        msg.extra_headers = {
            "List-Unsubscribe": f"<{unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    if attachments:
        for filename, content_type, data in attachments:
            msg.attach(filename, content_type, data)
    mail.send(msg)


def send_password_reset_email(to: str, reset_url: str):
    subject = "Reset Your Password — Book With Sheilla"
    body = (
        "You requested a password reset.\n\n"
        f"Click the link below to reset your password:\n{reset_url}\n\n"
        "This link will expire in 1 hour.\n\n"
        "If you did not request this, please ignore this email."
    )
    html = _base_html(
        preheader="Reset your Book With Sheilla password",
        content=f"""\
  <h2 style="margin:0 0 16px;font-family:'Noto Serif',Georgia,serif;font-size:20px;color:{_BRAND_TEXT};">
    Reset Your Password
  </h2>
  <p style="margin:0 0 12px;font-size:15px;line-height:1.6;color:{_BRAND_TEXT};">
    We received a request to reset your password. Click the button below to choose a new one.
  </p>
  <table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0;">
  <tr><td align="center" style="background:{_BRAND_GREEN};border-radius:8px;">
    <a href="{reset_url}" target="_blank"
       style="display:inline-block;padding:14px 36px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;">
      Reset Password
    </a>
  </td></tr>
  </table>
  <p style="margin:0 0 8px;font-size:13px;line-height:1.5;color:{_BRAND_MUTED};">
    This link will expire in <strong>1 hour</strong>.
  </p>
  <p style="margin:0;font-size:13px;line-height:1.5;color:{_BRAND_MUTED};">
    If you didn't request this, you can safely ignore this email.
  </p>""",
    )
    send_email(to=to, subject=subject, body=body, html=html)


def send_email_verification(to: str, verify_url: str):
    subject = "Verify Your Email — Book With Sheilla"
    body = (
        "Welcome! Please verify your email address.\n\n"
        f"Click the link below to verify:\n{verify_url}\n\n"
        "This link will expire in 24 hours."
    )
    html = _base_html(
        preheader="Verify your email to get started",
        content=f"""\
  <h2 style="margin:0 0 16px;font-family:'Noto Serif',Georgia,serif;font-size:20px;color:{_BRAND_TEXT};">
    Verify Your Email
  </h2>
  <p style="margin:0 0 12px;font-size:15px;line-height:1.6;color:{_BRAND_TEXT};">
    Welcome! Please confirm your email address by clicking the button below.
  </p>
  <table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0;">
  <tr><td align="center" style="background:{_BRAND_GREEN};border-radius:8px;">
    <a href="{verify_url}" target="_blank"
       style="display:inline-block;padding:14px 36px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;">
      Verify Email
    </a>
  </td></tr>
  </table>
  <p style="margin:0;font-size:13px;line-height:1.5;color:{_BRAND_MUTED};">
    This link will expire in <strong>24 hours</strong>.
  </p>""",
    )
    send_email(to=to, subject=subject, body=body, html=html)


def send_user_invitation(to: str, inviter_name: str, tenant_name: str, invite_url: str):
    subject = f"You've been invited to join {tenant_name}"
    body = (
        f"{inviter_name} has invited you to join {tenant_name}.\n\n"
        f"Click the link below to accept the invitation and create your account:\n{invite_url}\n\n"
        "This invitation will expire in 7 days."
    )
    html = _base_html(
        preheader=f"{inviter_name} has invited you to join {tenant_name}",
        content=f"""\
  <h2 style="margin:0 0 16px;font-family:'Noto Serif',Georgia,serif;font-size:20px;color:{_BRAND_TEXT};">
    You're Invited
  </h2>
  <p style="margin:0 0 12px;font-size:15px;line-height:1.6;color:{_BRAND_TEXT};">
    <strong>{inviter_name}</strong> has invited you to join <strong>{tenant_name}</strong>.
  </p>
  <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:{_BRAND_TEXT};">
    Click the button below to accept the invitation and create your account.
  </p>
  <table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0;">
  <tr><td align="center" style="background:{_BRAND_GREEN};border-radius:8px;">
    <a href="{invite_url}" target="_blank"
       style="display:inline-block;padding:14px 36px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;">
      Accept Invitation
    </a>
  </td></tr>
  </table>
  <p style="margin:0;font-size:13px;line-height:1.5;color:{_BRAND_MUTED};">
    This invitation will expire in <strong>7 days</strong>.
  </p>""",
    )
    send_email(to=to, subject=subject, body=body, html=html)
