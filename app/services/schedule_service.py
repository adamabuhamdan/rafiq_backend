"""
Schedule Service — Smart medication scheduling engine using Gemini AI.
Unified to send both system instructions and user data to the AI.
"""
import json
import re
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from app.core.config import get_settings

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)

WEEKDAY_ORDER = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]

async def suggest_primary_schedule(
    disease: str,
    wake_time: str,
    sleep_time: str,
    dosage_frequency: str,
    existing_meds: Optional[List[Dict]] = None,
) -> Dict[str, List[str]]:
    """اقتراح مواعيد للأدوية الأساسية باستخدام Gemini مع مراعاة الحالة المرضية."""
    system_prompt = _build_system_prompt(is_primary=True)
    user_prompt = f"""
المريض يعاني من مرض: {disease}
وقت الاستيقاظ: {wake_time}
وقت النوم: {sleep_time}
تعليمات الدواء (dosage_frequency): {dosage_frequency}

الأدوية الحالية (تجنب التعارض):
{_format_existing_meds(existing_meds) if existing_meds else "لا يوجد"}
"""
    return await _call_gemini_for_schedule(system_prompt, user_prompt)

async def suggest_secondary_schedule(
    dosage_frequency: str,
    wake_time: str,
    sleep_time: str,
    existing_primary_times: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """اقتراح مواعيد للأدوية الثانوية لتتوزع حول الأدوية الأساسية."""
    system_prompt = _build_system_prompt(is_primary=False)
    user_prompt = f"""
وقت الاستيقاظ: {wake_time}
وقت النوم: {sleep_time}
تعليمات الدواء: {dosage_frequency}

الأوقات المحجوزة للأدوية الأساسية:
{existing_primary_times if existing_primary_times else "لا يوجد"}
"""
    return await _call_gemini_for_schedule(system_prompt, user_prompt)

def _build_system_prompt(is_primary: bool) -> str:
    """بناء تعليمات النظام الصارمة لـ Gemini."""
    base = """
أنت خبير صيدلاني وجدولة أدوية. أجب بصيغة JSON فقط: {"weekdays": [...], "times": ["HH:MM", ...]}
القواعد:
1. التنسيق: الوقت بنظام 24 ساعة (HH:MM)، الأيام: ["sun","mon","tue","wed","thu","fri","sat"].
2. التعارض: يجب وجود 120 دقيقة (ساعتان) فرق بين أي وقت مقترح والأوقات المحجوزة.
3. فترة الاستيقاظ: جميع المواعيد يجب أن تكون بين وقت الاستيقاظ ووقت النوم حصراً.
4. الالتزام بالنص: إذا قيل 'مرة يومياً بعد العشاء' اقترح موعداً واحداً فقط قريباً من وقت النوم (مثلاً 21:00).
"""
    if is_primary:
        base += "\n5. الأدوية الأساسية: راعِ أن السكري يحتاج جرعات حول الوجبات (إفطار/عشاء)، والضغط عند الاستيقاظ."
    else:
        base += "\n5. الأدوية الثانوية: وزع الجرعات بالتساوي بعيداً عن أوقات الأدوية الأساسية."
    return base

async def _call_gemini_for_schedule(system_prompt: str, user_prompt: str) -> Dict[str, List[str]]:
    """إرسال التعليمات والطلب معاً لـ Gemini ومعالجة الرد."""
    model = genai.GenerativeModel("gemini-2.5-flash") 
    
    # دمج البرومبت لضمان قراءة التعليمات
    full_prompt = f"{system_prompt}\n\nبيانات المريض والطلب:\n{user_prompt}"
    
    response = model.generate_content(full_prompt)
    try:
        raw = re.sub(r"^```[a-z]*\n?|```$", "", response.text.strip())
        data = json.loads(raw)
        return {
            "weekdays": [d for d in data.get("weekdays", []) if d in WEEKDAY_ORDER] or WEEKDAY_ORDER.copy(),
            "times": data.get("times", ["09:00"])
        }
    except Exception:
        return {"weekdays": WEEKDAY_ORDER.copy(), "times": ["09:00"]}

def _format_existing_meds(existing_meds: List[Dict]) -> str:
    return "\n".join([f"- {m.get('name')}: {m.get('times')}" for m in existing_meds])