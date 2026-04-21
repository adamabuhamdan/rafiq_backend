"""
Email Service — sends emails via Resend SDK (primary) or SendGrid (fallback).
Configure EMAIL_PROVIDER in .env to choose between 'resend' and 'sendgrid'.

Resend docs: https://resend.com/docs/send-with-fastapi
"""
import resend
import httpx
import markdown
from app.core.config import get_settings

settings = get_settings()


def _send_via_resend(to: str, subject: str, html: str, api_key: str) -> bool:
    """Send an email using the official Resend Python SDK."""
    resend.api_key = api_key

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


async def send_email(to: str, subject: str, html: str, api_key_type: int = 1) -> bool:
    """
    Send an email using the configured provider.
    Falls back to console logging in development mode.
    """
    if settings.app_env == "development" and not settings.resend_api_key_1 and not settings.sendgrid_api_key:
        print(f"[DEV EMAIL] To: {to} | Subject: {subject}")
        print(f"[DEV EMAIL] Body preview: {html[:120]}...")
        return True

    try:
        if settings.email_provider == "resend":
            api_key = settings.resend_api_key_1 if api_key_type == 1 else settings.resend_api_key_2
            return _send_via_resend(to, subject, html, api_key)  # Resend SDK is sync
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
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #fdf2f2;
                margin: 0;
                padding: 20px;
                color: #333333;
            }}
            .email-wrapper {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(229, 62, 62, 0.1);
                overflow: hidden;
                border: 1px solid #fbd38d;
            }}
            .header {{
                background: linear-gradient(135deg, #e53e3e, #c53030);
                color: #ffffff;
                padding: 30px 20px;
                text-align: center;
                border-bottom: 4px solid #fc8181;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                letter-spacing: 0.5px;
            }}
            .header p {{
                margin: 10px 0 0 0;
                font-size: 16px;
                opacity: 0.9;
            }}
            .content {{
                padding: 35px 30px;
                line-height: 1.8;
                font-size: 16px;
                text-align: center;
            }}
            .alert-box {{
                background-color: #fff5f5;
                border: 1px solid #fed7d7;
                border-radius: 8px;
                padding: 20px;
                margin-top: 20px;
                color: #c53030;
                font-weight: bold;
                font-size: 18px;
            }}
            .footer {{
                background-color: #f8fafc;
                text-align: center;
                padding: 20px;
                font-size: 13px;
                color: #718096;
                border-top: 1px solid #e2e8f0;
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="header">
                <h1>⚠️ تنبيه أمان</h1>
                <p>إشعار بخصوص الالتزام بالدواء للمريض <strong>{patient_name}</strong></p>
            </div>
            <div class="content">
                <p>مرحباً،</p>
                <p>نود إعلامك بأن المريض لم يقم بتسجيل أخذ الجرعة المقررة في الوقت المحدد.</p>
                <div class="alert-box">
                    الدواء: {medication_name}
                </div>
                <p style="margin-top: 25px; color: #4a5568;">
                    يُرجى التواصل مع المريض للتأكد من التزامه بالعلاج وحالته الصحية.<br>
                    شكراً لتعاونكم.
                </p>
            </div>
            <div class="footer">
                <p>هذا الإشعار تم إرساله آلياً بواسطة تطبيق <strong>"رفيق"</strong>.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return await send_email(to, subject, html, api_key_type=1)


async def send_weekly_doctor_report_email(
    to: str,
    patient_name: str,
    report_html: str,
) -> bool:
    """Send a weekly medical report email to the treating physician."""
    subject = f"📋 التقرير الأسبوعي لمريض: {patient_name}"
    
    # 1. تحويل نص Gemini (Markdown) إلى HTML حقيقي
    # استخدام extensions=['extra'] يساعد في تحويل الجداول والقوائم المتداخلة بشكل أفضل
    formatted_content = markdown.markdown(report_html, extensions=['extra'])

    # 2. بناء قالب الإيميل الاحترافي (المحفزات البصرية)
    html = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f7f6;
                margin: 0;
                padding: 20px;
                color: #333333;
            }}
            .email-wrapper {{
                max-width: 650px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #2b6cb0, #2c5282);
                color: #ffffff;
                padding: 30px 20px;
                text-align: center;
                border-bottom: 4px solid #63b3ed;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                letter-spacing: 0.5px;
            }}
            .header p {{
                margin: 10px 0 0 0;
                font-size: 16px;
                opacity: 0.9;
            }}
            .content {{
                padding: 35px 30px;
                line-height: 1.8;
                font-size: 15px;
            }}
            /* تنسيق العناوين التي يولدها الذكاء الاصطناعي */
            .content h1, .content h2, .content h3 {{
                color: #2b6cb0;
                border-bottom: 2px solid #edf2f7;
                padding-bottom: 8px;
                margin-top: 30px;
                margin-bottom: 15px;
            }}
            .content strong {{
                color: #1a365d;
                background-color: #ebf8ff; /* تمييز خفيف للنصوص العريضة */
                padding: 2px 5px;
                border-radius: 4px;
            }}
            .content ul, .content ol {{
                padding-right: 25px;
                margin-bottom: 20px;
            }}
            .content li {{
                margin-bottom: 12px;
            }}
            .footer {{
                background-color: #f8fafc;
                text-align: center;
                padding: 20px;
                font-size: 13px;
                color: #718096;
                border-top: 1px solid #e2e8f0;
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="header">
                <h1>التقرير الطبي الأسبوعي</h1>
                <p>سجل المتابعة الدورية للمريض: <strong>{patient_name}</strong></p>
            </div>
            <div class="content">
                {formatted_content}
            </div>
            <div class="footer">
                <p>تم إعداد هذا التقرير وتحليله آلياً بواسطة نظام <strong>"رفيق"</strong> الذكي.</p>
                <p>يُرجى مراجعة البيانات مع المريض لاتخاذ القرار الطبي المناسب.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return await send_email(to, subject, html, api_key_type=2)
