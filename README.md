# وثيقة مشروع: تطبيق "رفيق" (Rafiq) - المساعد الطبي الشخصي (Backend v2.1)

**الرؤية:** منصة تكنولوجيا صحية (HealthTech) تعمل كمساعد طبي شخصي ذكي لإدارة الأمراض المزمنة. يعتمد النظام على ذكاء اصطناعي "وكيل" (Agentic AI) يربط بين التشخيص الإكلينيكي والخدمات الوظيفية (الصيدلة والتقارير).
**المساعد الذكي:** "مادو" (Mado) - نظام متعدد الوكلاء (Multi-Agent System).

---

## 🛠 المكدس التقني (Tech Stack)
*   **الواجهة الخلفية (Backend):** FastAPI / Python 3.11+.
*   **إدارة البيئة:** Windows/Linux مع `venv` و `pip`.
*   **قاعدة البيانات والمصادقة:** Supabase (PostgreSQL) لإدارة المستخدمين، الأدوية، والرسائل.
*   **قاعدة البيانات المتجهة (Vector DB):** Qdrant (لتخزين المراجع الطبية بصيغة Embeddings).
*   **محرك الذكاء الاصطناعي:** Gemini 2.5 Flash (عبر مكتبة `google-generativeai`).
*   **النماذج المتضمنة:** 
    *   `gemini-2.5-flash`: للمحادثة والتحليل والتقارير والرؤية (Vision).
    *   `models/gemini-embedding-001`: لعمليات الـ RAG (استرجاع المعلومات).

---

## 🚀 التشغيل السريع (Quick Start)

### 1. تثبيت المتطلبات (Installation)
تأكد من وجود Python 3.11 مثبت على جهازك، ثم قم بتشغيل الأوامر التالية:

```bash
# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة (Windows)
.\venv\Scripts\activate

# تفعيل البيئة (Linux/Mac)
source venv/bin/activate

# تثبيت المكتبات المطلوبة
pip install -r requirements.txt
```

### 2. إعداد المتغيرات (Environment Setup)
قم بإنشاء ملف `.env` في المجلد الرئيسي وأضف المفاتيح التالية:
```env
GEMINI_API_KEY=your_gemini_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
```

### 3. تشغيل السيرفر (Running the Server)
لتشغيل المشروع في وضع التطوير (Development Mode):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🧠 هندسة النظام (Multi-Agent Ecosystem)

1.  **الوكيل الموجِّه (Orchestrator):** يصنف النية (Intent) ويستدعي الوكلاء المتخصصين بالتوازي.
2.  **الوكلاء الإكلينيكيون (Clinical Agents):** يعملون بنظام RAG مخصص لكل مرض (سكري، ضغط، غدد).
3.  **وكيل الصيدلة (Pharmacy Agent):** 
    *   **Clinical Safety Pivot:** تم تعديل منطق مسح الصور لاستخراج (الاسم والمادة الفعالة) فقط من "علب الدواء" وتجاهل الروشتات المكتوبة يدوياً لضمان السلامة ومنع الهلوسة البرمجية.
    *   **Smart Scheduling:** يدعم الجدولة الذكية (Primary/Secondary) وتخزين التعليمات في حقل `ai_instruction`.
    *   **Upsert Logic:** النظام يدعم التحديث الذكي للأدوية لمنع التكرار في قاعدة البيانات.

---

## 📂 الهيكلية المعمارية (Folder Structure)

```text
rafiq_backend/
├── app/
│   ├── api/routes/             # مسارات FastAPI (Chat, Pharmacy, Reports, Auth)
│   ├── core/                   # الإعدادات (Config) والـ Prompts المركزية
│   ├── agents/                 # الوكلاء (Orchestrator, Clinical, Functional)
│   ├── schemas/                # نماذج Pydantic للتحقق من البيانات (Pydantic Models)
│   ├── services/               # منطق الخدمة المستقل (Scheduling, DB Logic)
│   └── db/                     # عملاء قاعدة البيانات (Supabase, Qdrant)
├── requirements.txt            # قائمة المكتبات
└── .env                        # متغيرات البيئة (مخفي)
```

---

## 🔌 دليل المطور للواجهة الأمامية (Frontend Guide)

*   **Chat API:** أرسل `language: "ar"` أو `"en"` للتحكم في لغة الرد.
*   **Pharmacy Scan:** يعيد الآن مصفوفة (Array) من الأدوية المستخرجة من الصورة الواحدة.
*   **Upsert Support:** تأكد من إرسال الـ `id` الخاص بالدواء عند التحديث لضمان عدم تكراره.
*   **AI Instruction:** حقل جديد في الداتابيس لعرض نصائح الجدولة الذكية للمريض.

---

> [!IMPORTANT]
> يمنع السيرفر استخراج الجرعات (Dosage) آلياً من الصور؛ يجب على المريض إدخالها يدوياً لضمان الدقة الطبية الكاملة وتجنب المسؤولية القانونية.