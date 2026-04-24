"""
Email Service — sends emails via Resend SDK (primary) or SendGrid (fallback).
"""
import os
import traceback
import resend
import httpx
import markdown
from app.core.config import get_settings

settings = get_settings()

def _send_via_resend(to: str, subject: str, html: str, api_key: str) -> bool:
    """Send an email using the official Resend Python SDK."""
    resend.api_key = api_key
    
    # حماية من الانهيار في حال لم يكن from_email موجوداً في إعدادات config
    from_email = getattr(settings, "from_email", os.getenv("FROM_EMAIL", "onboarding@resend.dev"))

    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    email: resend.Emails.SendResponse = resend.Emails.send(params)
    return bool(email.get("id"))

async def _send_via_sendgrid(to: str, subject: str, html: str) -> bool:
    """Send an email using the SendGrid Web API v3."""
    sg_key = getattr(settings, "sendgrid_api_key", os.getenv("SENDGRID_API_KEY"))
    from_email = getattr(settings, "from_email", os.getenv("FROM_EMAIL"))
    
    headers = {
        "Authorization": f"Bearer {sg_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": from_email},
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

async def send_email(to: str, subject: str, html: str, api_key_type: int = 1) -> bool:
    """Send an email using the configured provider."""
    try:
        # جلب المتغيرات بأمان تام لمنع خطأ 500
        app_env = getattr(settings, "app_env", os.getenv("APP_ENV", "production"))
        key1 = getattr(settings, "resend_api_key_1", os.getenv("RESEND_API_KEY_1"))
        key2 = getattr(settings, "resend_api_key_2", os.getenv("RESEND_API_KEY_2"))
        sg_key = getattr(settings, "sendgrid_api_key", os.getenv("SENDGRID_API_KEY"))
        provider = getattr(settings, "email_provider", os.getenv("EMAIL_PROVIDER", "resend"))

        if app_env == "development" and not key1 and not sg_key:
            print(f"[DEV EMAIL] To: {to} | Subject: {subject}")
            return True

        if provider == "resend":
            api_key = key1 if api_key_type == 1 else key2
            if not api_key:
                print("❌ [ERROR] Resend API Key is missing or not loaded!")
                return False
            return _send_via_resend(to, subject, html, api_key)
            
        elif provider == "sendgrid":
            return await _send_via_sendgrid(to, subject, html)
        else:
            print(f"[WARN] Unknown email provider: '{provider}'")
            return False
            
    except Exception as e:
        print(f"\n❌ [CRITICAL ERROR] Failed to send email to {to}")
        print(f"Error Details: {e}")
        traceback.print_exc()  # هذا السطر سيكشف لنا العطل الحقيقي في الـ Terminal
        return False

async def send_missed_dose_email(to: str, patient_name: str, medication_name: str) -> bool:
    subject = f"⚠️ تنبيه: {patient_name} لم يأخذ دواءه"
    html = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #fdf2f2; margin: 0; padding: 20px; color: #333333; }}
            .email-wrapper {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #fbd38d; }}
            .header {{ background: linear-gradient(135deg, #e53e3e, #c53030); color: #ffffff; padding: 30px 20px; text-align: center; }}
            .content {{ padding: 35px 30px; text-align: center; }}
            .alert-box {{ background-color: #fff5f5; border: 1px solid #fed7d7; border-radius: 8px; padding: 20px; margin-top: 20px; color: #c53030; font-weight: bold; font-size: 18px; }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="header"><h1>⚠️ تنبيه أمان</h1><p>إشعار بخصوص المريض <strong>{patient_name}</strong></p></div>
            <div class="content">
                <p>مرحباً، نود إعلامك بأن المريض <strong>{patient_name}</strong> لم يقم بتسجيل أخذ الجرعة المقررة.</p>
                <div class="alert-box">الدواء: {medication_name}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return await send_email(to, subject, html, api_key_type=1)

async def send_weekly_doctor_report_email(to: str, patient_name: str, report_html: str) -> bool:
    subject = f"📋 التقرير الأسبوعي لمريض: {patient_name}"
    formatted_content = markdown.markdown(report_html, extensions=['extra'])
    html = f"""
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"></head>
    <body>
        <div style="max-width: 650px; margin: 0 auto; font-family: sans-serif;">
            <h2 style="color: #2b6cb0;">التقرير الطبي الأسبوعي: {patient_name}</h2>
            <div>{formatted_content}</div>
        </div>
    </body>
    </html>
    """
    return await send_email(to, subject, html, api_key_type=2)