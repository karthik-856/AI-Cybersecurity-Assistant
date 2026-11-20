import html
import smtplib
import ssl
from email.message import EmailMessage

from backend.app.core.config import settings


class EmailConfigurationError(RuntimeError):
    """Raised when SMTP configuration is incomplete."""


def check_email_connection() -> dict:
    """Authenticate without sending mail; expose only safe failure categories."""
    missing = missing_smtp_settings()
    if missing:
        return {"connected": False, "stage": "configuration", "error_code": "missing_settings",
                "message": "Missing settings: " + ", ".join(missing)}
    stage = "connect"
    try:
        context = ssl.create_default_context()
        connection = (smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=10)
                      if settings.smtp_use_ssl else smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10))
        with connection as server:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:
                stage = "tls"
                server.starttls(context=context)
            stage = "authenticate"
            server.login(settings.smtp_username, settings.smtp_password)
        return {"connected": True, "stage": "authenticated", "error_code": None,
                "message": "SMTP authentication succeeded. Send a verification code to test delivery."}
    except smtplib.SMTPAuthenticationError:
        code, message = "authentication_failed", "The provider rejected the SMTP login/key or account activation."
    except ssl.SSLError:
        code, message = "tls_failed", "The TLS connection failed. Check SMTP port and SSL/STARTTLS settings."
    except TimeoutError:
        code, message = "connection_timeout", "The SMTP connection timed out."
    except (OSError, smtplib.SMTPException):
        code, message = "connection_failed", "The SMTP connection failed. Check provider and transport settings."
    return {"connected": False, "stage": stage, "error_code": code, "message": message}


def missing_smtp_settings() -> list[str]:
    required = {
        "SMTP_HOST": settings.smtp_host,
        "SMTP_USERNAME": settings.smtp_username,
        "SMTP_PASSWORD": settings.smtp_password,
        "SMTP_FROM_EMAIL": settings.smtp_from_email,
    }

    return [
        name
        for name, value in required.items()
        if not value or not value.strip()
    ]


def _validate_smtp_configuration() -> None:
    missing = missing_smtp_settings()
    if missing:
        raise EmailConfigurationError(
            "SMTP email service is not configured. "
            f"Missing: {', '.join(missing)}"
        )


def _send_email(
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    _validate_smtp_configuration()

    message = EmailMessage()

    message["Subject"] = subject
    message["From"] = (
        f"{settings.smtp_from_name} "
        f"<{settings.smtp_from_email}>"
    )
    message["To"] = recipient

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            context=context,
            timeout=20,
        ) as server:
            server.login(
                settings.smtp_username,
                settings.smtp_password,
            )
            server.send_message(message)

        return

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=20,
    ) as server:

        if settings.smtp_use_tls:
            server.starttls(context=context)

        server.login(
            settings.smtp_username,
            settings.smtp_password,
        )

        server.send_message(message)


def send_email_verification_otp(
    recipient: str = "",
    username: str = "User",
    otp: str = "",
    *,
    recipient_email: str | None = None,
) -> None:
    target_recipient = recipient or recipient_email or ""
    safe_username = html.escape(username)

    subject = "ZUKA — Verify Your Email Address"

    text_body = f"""
Hello {username},

Welcome to ZUKA Security Operations Center.

Your email verification code is:

{otp}

This code expires in {settings.otp_expiry_minutes} minutes.

If you did not create a ZUKA account, you can safely ignore this email.

Regards,
ZUKA Security Operations Center
""".strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ZUKA Email Verification</title>
</head>

<body style="
    margin:0;
    padding:0;
    background:#0b1220;
    font-family:Arial,Helvetica,sans-serif;
">

<div style="
    max-width:600px;
    margin:40px auto;
    background:#111827;
    border:1px solid #263244;
    border-radius:14px;
    overflow:hidden;
">

    <div style="
        padding:28px;
        background:#0f172a;
        border-bottom:1px solid #263244;
    ">
        <div style="
            font-size:24px;
            font-weight:700;
            color:#f8fafc;
        ">
            ZUKA
        </div>

        <div style="
            margin-top:5px;
            font-size:13px;
            color:#94a3b8;
        ">
            Security Operations Center
        </div>
    </div>

    <div style="padding:32px;">

        <p style="color:#e2e8f0;font-size:15px;">
            Hello {safe_username},
        </p>

        <p style="color:#cbd5e1;font-size:15px;line-height:1.6;">
            Welcome to ZUKA. Please verify your email address
            to activate your account.
        </p>

        <div style="
            margin:28px 0;
            padding:22px;
            text-align:center;
            background:#0b1220;
            border:1px solid #334155;
            border-radius:12px;
        ">

            <div style="
                color:#94a3b8;
                font-size:12px;
                text-transform:uppercase;
                letter-spacing:1px;
            ">
                Verification Code
            </div>

            <div style="
                margin-top:12px;
                font-size:34px;
                font-weight:700;
                letter-spacing:8px;
                color:#f8fafc;
            ">
                {otp}
            </div>

            <div style="
                margin-top:12px;
                color:#94a3b8;
                font-size:12px;
            ">
                Expires in {settings.otp_expiry_minutes} minutes
            </div>

        </div>

        <p style="
            color:#94a3b8;
            font-size:13px;
            line-height:1.6;
        ">
            If you did not create this account, no action is required.
        </p>

    </div>

    <div style="
        padding:20px 32px;
        background:#0f172a;
        color:#64748b;
        font-size:12px;
    ">
        ZUKA Security Operations Center
    </div>

</div>

</body>
</html>
""".strip()

    _send_email(
        recipient=target_recipient,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def send_password_reset_otp(
    recipient: str,
    username: str,
    otp: str,
) -> None:
    safe_username = html.escape(username)

    subject = "ZUKA — Password Reset Code"

    text_body = f"""
Hello {username},

A password reset was requested for your ZUKA Security Operations Center account.

Your password reset code is:

{otp}

This code expires in {settings.otp_expiry_minutes} minutes.

If you did not request a password reset, you can safely ignore this email.

Regards,
ZUKA Security Operations Center
""".strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ZUKA Password Reset</title>
</head>

<body style="
    margin:0;
    padding:0;
    background:#0b1220;
    font-family:Arial,Helvetica,sans-serif;
">

<div style="
    max-width:600px;
    margin:40px auto;
    background:#111827;
    border:1px solid #263244;
    border-radius:14px;
    overflow:hidden;
">

    <div style="
        padding:28px;
        background:#0f172a;
        border-bottom:1px solid #263244;
    ">
        <div style="
            font-size:24px;
            font-weight:700;
            color:#f8fafc;
        ">
            ZUKA
        </div>

        <div style="
            margin-top:5px;
            font-size:13px;
            color:#94a3b8;
        ">
            Security Operations Center
        </div>
    </div>

    <div style="padding:32px;">

        <p style="color:#e2e8f0;font-size:15px;">
            Hello {safe_username},
        </p>

        <p style="
            color:#cbd5e1;
            font-size:15px;
            line-height:1.6;
        ">
            We received a request to reset your ZUKA account password.
        </p>

        <div style="
            margin:28px 0;
            padding:22px;
            text-align:center;
            background:#0b1220;
            border:1px solid #334155;
            border-radius:12px;
        ">

            <div style="
                color:#94a3b8;
                font-size:12px;
                text-transform:uppercase;
                letter-spacing:1px;
            ">
                Password Reset Code
            </div>

            <div style="
                margin-top:12px;
                font-size:34px;
                font-weight:700;
                letter-spacing:8px;
                color:#f8fafc;
            ">
                {otp}
            </div>

            <div style="
                margin-top:12px;
                color:#94a3b8;
                font-size:12px;
            ">
                Expires in {settings.otp_expiry_minutes} minutes
            </div>

        </div>

        <p style="
            color:#94a3b8;
            font-size:13px;
            line-height:1.6;
        ">
            If you did not request this password reset, no action is
            required. Your current password remains unchanged.
        </p>

    </div>

    <div style="
        padding:20px 32px;
        background:#0f172a;
        color:#64748b;
        font-size:12px;
    ">
        ZUKA Security Operations Center
    </div>

</div>

</body>
</html>
""".strip()

    _send_email(
        recipient=recipient,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )

def send_two_factor_otp(
    recipient: str,
    username: str,
    otp: str,
    purpose: str,
) -> None:
    """Send an OTP used for ZUKA two-step verification."""
    safe_username = html.escape(username)
    safe_purpose = html.escape(purpose)

    subject = (
        "ZUKA — Two-Step Verification Code"
        if purpose == "2FA"
        else "ZUKA — Login Verification Code"
    )

    text_body = f"""
Hello {username},

Your ZUKA Security Operations Center {purpose.lower()} verification code is:

{otp}

This code expires in {settings.otp_expiry_minutes} minutes.

If you did not request this code, please secure your ZUKA account and review your login activity.

Regards,
ZUKA Security Operations Center
""".strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ZUKA Two-Step Verification</title>
</head>
<body style="margin:0;padding:0;background:#0b1220;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:600px;margin:40px auto;background:#111827;border:1px solid #263244;border-radius:14px;overflow:hidden;">
    <div style="padding:28px;background:#0f172a;border-bottom:1px solid #263244;">
        <div style="font-size:24px;font-weight:700;color:#f8fafc;">ZUKA</div>
        <div style="margin-top:5px;font-size:13px;color:#94a3b8;">Security Operations Center</div>
    </div>

    <div style="padding:32px;">
        <p style="color:#e2e8f0;font-size:15px;">Hello {safe_username},</p>

        <p style="color:#cbd5e1;font-size:15px;line-height:1.6;">
            Your ZUKA {safe_purpose.lower()} verification code is below.
        </p>

        <div style="margin:28px 0;padding:22px;text-align:center;background:#0b1220;border:1px solid #334155;border-radius:12px;">
            <div style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:1px;">
                Verification Code
            </div>
            <div style="margin-top:12px;font-size:34px;font-weight:700;letter-spacing:8px;color:#f8fafc;">
                {otp}
            </div>
            <div style="margin-top:12px;color:#94a3b8;font-size:12px;">
                Expires in {settings.otp_expiry_minutes} minutes
            </div>
        </div>

        <p style="color:#94a3b8;font-size:13px;line-height:1.6;">
            If you did not request this code, please secure your account and review your login activity.
        </p>
    </div>

    <div style="padding:20px 32px;background:#0f172a;color:#64748b;font-size:12px;">
        ZUKA Security Operations Center
    </div>
</div>
</body>
</html>
""".strip()

    _send_email(
        recipient=recipient,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def send_analyst_approval_email(
    recipient: str,
    analyst_username: str,
    analyst_email: str,
    analyst_id: int,
    approval_token: str,
    approval_url: str | None = None,
) -> None:
    """Send an authorization request email to administrator for new SOC Analyst accounts."""
    safe_username = html.escape(analyst_username)
    safe_analyst_email = html.escape(analyst_email)

    url = approval_url or f"http://127.0.0.1:8000/api/admin/users/{analyst_id}/approve-via-mail?token={approval_token}"

    subject = f"ZUKA SOC — Action Required: Approve SOC Analyst '{analyst_username}'"

    text_body = f"""
Hello Administrator,

A new SOC Analyst account has been registered on ZUKA Security Operations Center and requires your authorization:

- Username: {analyst_username}
- Email: {analyst_email}
- Account ID: #{analyst_id}
- Requested Role: SOC_ANALYST
- Current Status: PENDING_APPROVAL (Inactive)

To approve this account and allow the analyst to access the SOC platform, click the link below:

{url}

You can also approve or reject this analyst directly in the ZUKA User Management console (http://127.0.0.1:5173/users).

Regards,
ZUKA Security Operations Center
""".strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ZUKA SOC — Analyst Approval Required</title>
</head>
<body style="margin:0;padding:0;background:#0b1220;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:600px;margin:40px auto;background:#111827;border:1px solid #263244;border-radius:14px;overflow:hidden;box-shadow:0 12px 30px rgba(0,0,0,0.5);">
    <div style="padding:28px;background:#0f172a;border-bottom:1px solid #263244;display:flex;align-items:center;">
        <div>
            <div style="font-size:24px;font-weight:700;color:#f8fafc;letter-spacing:1px;">ZUKA SOC</div>
            <div style="margin-top:4px;font-size:12.5px;color:#38bdf8;font-weight:600;">IDENTITY & ACCESS GOVERNANCE</div>
        </div>
    </div>

    <div style="padding:32px;">
        <div style="display:inline-block;padding:4px 10px;background:#78350f;color:#fef3c7;border-radius:6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:16px;">
            Action Required • Account Approval
        </div>

        <h2 style="margin:0 0 14px;color:#f8fafc;font-size:19px;font-weight:700;">
            SOC Analyst Authorization Request
        </h2>

        <p style="color:#cbd5e1;font-size:14px;line-height:1.6;margin-bottom:24px;">
            A new user has been created with the <strong style="color:#38bdf8;">SOC_ANALYST</strong> role. In accordance with zero-trust security policy, this account has been provisioned in an <strong>inactive pending state</strong> until authorized by an administrator.
        </p>

        <div style="background:#0b1220;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:28px;">
            <table style="width:100%;border-collapse:collapse;font-size:13.5px;">
                <tr>
                    <td style="padding:7px 0;color:#94a3b8;width:140px;font-weight:600;">Analyst Username:</td>
                    <td style="padding:7px 0;color:#f8fafc;font-weight:700;">{safe_username}</td>
                </tr>
                <tr>
                    <td style="padding:7px 0;color:#94a3b8;font-weight:600;">Email Address:</td>
                    <td style="padding:7px 0;color:#38bdf8;font-family:monospace;">{safe_analyst_email}</td>
                </tr>
                <tr>
                    <td style="padding:7px 0;color:#94a3b8;font-weight:600;">Assigned Role:</td>
                    <td style="padding:7px 0;color:#10b981;font-weight:700;">SOC_ANALYST</td>
                </tr>
                <tr>
                    <td style="padding:7px 0;color:#94a3b8;font-weight:600;">Account Record ID:</td>
                    <td style="padding:7px 0;color:#e2e8f0;font-family:monospace;">#{analyst_id}</td>
                </tr>
                <tr>
                    <td style="padding:7px 0;color:#94a3b8;font-weight:600;">Status:</td>
                    <td style="padding:7px 0;color:#f59e0b;font-weight:700;">⏳ PENDING ADMIN APPROVAL</td>
                </tr>
            </table>
        </div>

        <div style="text-align:center;margin:32px 0;">
            <a href="{url}" style="display:inline-block;background:#0284c7;color:#ffffff;text-decoration:none;font-weight:700;font-size:14px;padding:14px 32px;border-radius:8px;box-shadow:0 4px 14px rgba(2,132,199,0.4);">
                ✔ Approve SOC Analyst Account
            </a>
        </div>

        <p style="color:#94a3b8;font-size:12.5px;line-height:1.6;margin-top:24px;border-top:1px solid #1e293b;padding-top:18px;">
            Alternatively, you can manage, activate, or reject this user directly in the <a href="http://127.0.0.1:5173/users" style="color:#38bdf8;text-decoration:none;">User Management Console</a>.
        </p>
    </div>

    <div style="padding:18px 32px;background:#0f172a;border-top:1px solid #1e293b;color:#64748b;font-size:11.5px;">
        ZUKA Security Operations Center • Automated Access Governance
    </div>
</div>
</body>
</html>
""".strip()

    _send_email(
        recipient=recipient,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )

