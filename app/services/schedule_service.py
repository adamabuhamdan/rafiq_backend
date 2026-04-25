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

async def suggest_comprehensive_schedule(
    diseases: List[str],
    wake_time: str,
    sleep_time: str,
    new_medications: List[Dict[str, Any]],
    existing_meds: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """اقتراح مواعيد لكل الأدوية الجديدة في طلب واحد لتجنب التعارضات."""
    system_prompt = _build_comprehensive_system_prompt()
    
    # تحضير قائمة الأدوية الجديدة كـ JSON
    import json
    new_meds_json = json.dumps([{
        "id": m.get("id", str(i)),
        "name": m.get("name"),
        "dosage_frequency": m.get("dosage_frequency"),
        "is_primary": m.get("is_primary", False)
    } for i, m in enumerate(new_medications)], ensure_ascii=False, indent=2)

    user_prompt = f"""
الأمراض: {', '.join(diseases) if diseases else 'لا يوجد'}
وقت الاستيقاظ: {wake_time}
وقت النوم: {sleep_time}

الأدوية الجديدة المطلوب جدولتها:
{new_meds_json}

الأدوية الحالية (تجنب التعارض معها):
{_format_existing_meds(existing_meds) if existing_meds else "لا يوجد"}
"""
    return await _call_gemini_for_comprehensive_schedule(system_prompt, user_prompt, new_medications)

def _build_comprehensive_system_prompt() -> str:
    """بناء تعليمات النظام الشاملة لـ Gemini."""
    return """
أنت خبير صيدلاني وجدولة أدوية. يجب أن ترد بصيغة JSON فقط، بدون أي نصوص إضافية أو Markdown.
الصيغة المطلوبة:
{
  "explanation": "شرح قصير بالعربية عن سبب اختيار هذه المواعيد وكيفية تجنب التعارض.",
  "suggestions": [
    {
      "id": "نفس المعرف ID المرسل لك",
      "weekdays": ["sun", "mon", "tue", "wed", "thu", "fri", "sat"],
      "times": ["HH:MM"],
      "ai_instruction": "نصيحة طبية قصيرة متعلقة بالدواء"
    }
  ]
}

القواعد:
1. التنسيق: الوقت بنظام 24 ساعة بدقة (HH:MM).
2. التعارض: تجنب التعارض بين الأدوية الجديدة نفسها، وبين الأدوية الجديدة والحالية. اترك ساعتين على الأقل بين الأدوية إلا إذا كانت آمنة معاً.
3. فترة الاستيقاظ: جميع المواعيد بين وقت الاستيقاظ ووقت النوم حصراً.
4. الأدوية الأساسية: راعِ أن أدوية السكري والضغط تحتاج مواعيد معينة (حول الوجبات أو عند الاستيقاظ).
5. التوقيت الدقيق (AM/PM الصارم): جرعات الصباح بين 05:00 و 11:59. جرعات المساء بين 17:00 و 23:59.
6. إذا كان الدواء "عند اللزوم"، اقترح أوقاتاً متباعدة منطقياً.
"""

async def _call_gemini_for_comprehensive_schedule(system_prompt: str, user_prompt: str, original_meds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """إرسال التعليمات والطلب معاً لـ Gemini ومعالجة الرد."""
    model = genai.GenerativeModel("gemini-2.5-flash") 
    
    full_prompt = f"{system_prompt}\n\nبيانات المريض والطلب:\n{user_prompt}"
    
    response = model.generate_content(full_prompt)
    try:
        raw = response.text.strip()
        # محاولة إيجاد JSON في حال أضاف Gemini نصوص إضافية
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(raw)
            
        # دمج الرد مع الأدوية الأصلية لضمان عدم ضياع أي بيانات
        suggestions = []
        ai_sug_map = {str(s.get("id")): s for s in data.get("suggestions", [])}
        
        for i, med in enumerate(original_meds):
            med_id = str(med.get("id", i))
            ai_data = ai_sug_map.get(med_id, {})
            
            suggestion = {
                "name": med.get("name"),
                "active_ingredient": med.get("active_ingredient"),
                "dosage_frequency": med.get("dosage_frequency"),
                "weekdays": [d for d in ai_data.get("weekdays", []) if d in WEEKDAY_ORDER] or WEEKDAY_ORDER.copy(),
                "times": ai_data.get("times", ["09:00"]),
                "is_primary": med.get("is_primary", False),
                "ai_instruction": ai_data.get("ai_instruction", "")
            }
            if "id" in med:
                suggestion["id"] = med["id"]
            suggestions.append(suggestion)

        return {
            "type": "comprehensive",
            "explanation": data.get("explanation", "تمت جدولة الأدوية بناءً على التعليمات."),
            "suggestions": suggestions
        }
    except Exception as e:
        print(f"Error parsing Gemini response: {e}, Raw: {response.text}")
        # fallback
        suggestions = []
        for med in original_meds:
            sug = med.copy()
            sug["weekdays"] = WEEKDAY_ORDER.copy()
            sug["times"] = ["09:00"]
            sug["ai_instruction"] = ""
            suggestions.append(sug)
        return {
            "type": "comprehensive",
            "explanation": "حدث خطأ في معالجة الذكاء الاصطناعي، تم تعيين مواعيد افتراضية.",
            "suggestions": suggestions
        }

def _format_existing_meds(existing_meds: List[Dict]) -> str:
    return "\n".join([f"- {m.get('name')}: {m.get('times')}" for m in existing_meds])