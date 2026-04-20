"""
Email Service — sends emails via Resend SDK (primary) or SendGrid (fallback).
Configure EMAIL_PROVIDER in .env to choose between 'resend' and 'sendgrid'.

Resend docs: https://resend.com/docs/send-with-fastapi
"""
import resend
import httpx
from app.core.config import get_settings

settings = get_settings()


def _send_via_resend(to: str, subject: str, html: str) -> bool:
    """Send an email using the official Resend Python SDK."""
    resend.api_key = settings.resend_api_key

    params: resend.Emails.SendParams = {
        "from": settings.from_email,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    email: resend.Emails.SendResponse = resend.Emails.send(params)
    # SDK raises on error; if we get here it succeeded
    return bool(email.get("id"))


async def _send_via_sendgrid(to: str, subject: str, html: str) -> bool:
    """Send an email using the SendGrid Web API v3."""
    headers = {
        "Authorization": f"Bearer {settings.sendgrid_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": settings.from_email},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
    return True


async def send_email(to: str, subject: str, html: str) -> bool:
    """
    Send an email using the configured provider.
    Falls back to console logging in development mode.
    """
    if settings.app_env == "development" and not settings.resend_api_key and not settings.sendgrid_api_key:
        print(f"[DEV EMAIL] To: {to} | Subject: {subject}")
        print(f"[DEV EMAIL] Body preview: {html[:120]}...")
        return True

    try:
        if settings.email_provider == "resend":
            return _send_via_resend(to, subject, html)  # Resend SDK is sync
        elif settings.email_provider == "sendgrid":
            return await _send_via_sendgrid(to, subject, html)
        else:
            print(f"[WARN] Unknown email provider: '{settings.email_provider}'. Use 'resend' or 'sendgrid'.")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to send email to {to}: {e}")
        return False


async def send_missed_dose_email(
    to: str,
    patient_name: str,
    medication_name: str,
) -> bool:
    """Send a missed dose alert email to a family member."""
    subject = f"⚠️ تنبيه: {patient_name} لم يأخذ دواءه"
    html = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; padding: 24px; max-width: 500px;">
        <h2 style="color: #e53e3e;">تنبيه جرعة فائتة</h2>
        <p>المريض <strong>{patient_name}</strong> لم يأخذ جرعة <strong>{medication_name}</strong> في الموعد المحدد.</p>
        <p>يُرجى التواصل معه للتأكد من التزامه بالعلاج.</p>
        <br>
        <p style="color: #718096; font-size: 12px;">— تطبيق رفيق</p>
    </div>
    """
    return await send_email(to, subject, html)


async def send_weekly_doctor_report_email(
    to: str,
    patient_name: str,
    report_html: str,
) -> bool:
    """Send a weekly medical report email to the treating physician."""
    subject = f"📋 التقرير الأسبوعي لمريض: {patient_name}"
    html = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; padding: 24px; max-width: 600px;">
        <h2 style="color: #2b6cb0;">التقرير الطبي الأسبوعي</h2>
        <p><strong>المريض:</strong> {patient_name}</p>
        <hr style="border-color: #e2e8f0;">
        <div>{report_html}</div>
        <br>
        <p style="color: #718096; font-size: 12px;">— تطبيق رفيق | نظام المتابعة الطبية الذكي</p>
    </div>
    """
    return await send_email(to, subject, html)
