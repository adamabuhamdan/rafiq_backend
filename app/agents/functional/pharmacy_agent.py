"""
Pharmacy Agent — unified for camera, schedule suggestions (primary/secondary), and interactions.
"""
import json
import re
import uuid  # 🛠️ تمت إضافة استدعاء مكتبة uuid هنا
from datetime import time
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from app.agents.tools.pharmacy_api import check_drug_interactions, MedicationInfo
from app.services.schedule_service import suggest_comprehensive_schedule
from app.db.supabase_client import get_supabase
from app.core.config import get_settings
from app.core.prompts import PRESCRIPTION_SCAN_PROMPT

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)


class PharmacyAgent:
    name = "pharmacy_agent"

    # ========== 1. Save medications (direct, no AI) ==========
    async def save_medications(self, patient_id: str, medications: list[dict]) -> dict:
        supabase = get_supabase()
        rows = []
        for m in medications:
            raw_id = m.get("id")

            # ── UUID validation ──────────────────────────────────────────────
            # Flutter generates temporary numeric IDs (e.g. "17767000084033670")
            # for new medications that haven't been saved yet.
            # Supabase requires a proper UUID — passing a numeric string causes
            # "invalid input syntax for type uuid" → HTTP 500.
            # Fix: only include the id field if it looks like a real UUID.
            is_real_uuid = bool(
                raw_id and
                re.fullmatch(
                    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                    raw_id
                )
            )

            row = {
                "patient_id": patient_id,
                "name": m["name"],
                "active_ingredient": m.get("active_ingredient"),
                "dosage_frequency": m.get("dosage_frequency"),
                "weekdays": m.get("weekdays", []),
                "times": m.get("times", []),
                "is_primary": m.get("is_primary", False),
                "ai_instruction": m.get("ai_instruction"),
            }

            # 🛠️ التعديل الجديد هنا: توليد ID حقيقي للأدوية الجديدة
            if is_real_uuid:
                row["id"] = raw_id # دواء قديم، نستخدم الـ ID الخاص به للتحديث
            else:
                row["id"] = str(uuid.uuid4()) # دواء جديد، نصنع له ID حقيقي فوراً

            rows.append(row)

        # upsert: updates existing records (by UUID) and inserts new ones
        supabase.table("medications").upsert(rows).execute()
        return {"saved_count": len(rows)}


    # ========== 2. Prescription scan (Camera) ==========
    async def scan_prescription(self, patient_id: str, image_base64: str, media_type: str = "image/jpeg") -> dict:
        extracted_list = await self._extract_from_image(image_base64, media_type)
        return {
            "extracted": extracted_list,
            "note": "تم استخراج الأدوية. يرجى إدخال الجرعة والتكرار لكل دواء يدوياً بناءً على تعليمات الطبيب لضمان سلامتك.",
        }

    # ========== 3. Smart schedule suggestion (using Gemini) ==========
    async def suggest_smart_schedule(
        self,
        patient_id: str,
        new_medications: List[Dict[str, Any]],
    ) -> dict:
        supabase = get_supabase()

        # Fetch patient data
        patient_res = supabase.table("patients").select("wake_time, sleep_time, diseases").eq("id", patient_id).single().execute()
        if not patient_res.data:
            raise ValueError(f"Patient {patient_id} not found")
        p = patient_res.data

        # Fetch existing medications (for conflict avoidance)
        existing_res = supabase.table("medications").select("weekdays, times, is_primary, name").eq("patient_id", patient_id).execute()
        existing_meds = existing_res.data or []

        return await suggest_comprehensive_schedule(
            diseases=p.get("diseases", []),
            wake_time=p["wake_time"],
            sleep_time=p["sleep_time"],
            new_medications=new_medications,
            existing_meds=existing_meds
        )

    # ========== 4. Interaction check ==========
    async def check_interactions(self, medications: list[dict]) -> dict:
        med_objects = [MedicationInfo(name=m["name"], active_ingredient=m.get("active_ingredient")) for m in medications]
        return await check_drug_interactions(med_objects)

    # ========== 5. Image extraction ==========
    async def _extract_from_image(self, image_base64: str, media_type: str) -> List[dict]:
        model = genai.GenerativeModel("gemini-2.5-flash")
        try:
            response = model.generate_content([
                {"mime_type": media_type, "data": image_base64},
                PRESCRIPTION_SCAN_PROMPT,
            ])
            raw = re.sub(r"^```[a-z]*\n?|```$", "", response.text.strip())
            data = json.loads(raw)
            
            if not isinstance(data, list):
                data = [data]
                
            # Normalize missing or null fields
            for item in data:
                if not item.get("name"):
                    item["name"] = "دواء غير معروف"
                if "active_ingredient" not in item:
                    item["active_ingredient"] = None
                
            return data
        except Exception:
            return [
                {
                    "name": "دواء غير معروف",
                    "active_ingredient": None,
                }
            ]