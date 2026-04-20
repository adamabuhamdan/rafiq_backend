"""
Pharmacy Agent — unified for camera, schedule suggestions (primary/secondary), and interactions.
"""
import json
import re
from datetime import time
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from app.agents.tools.pharmacy_api import check_drug_interactions, MedicationInfo
from app.services.schedule_service import suggest_primary_schedule, suggest_secondary_schedule
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
            row = {
                "id": m.get("id"), # ✅ تمرير الـ ID
                "patient_id": patient_id,
                "name": m["name"],
                "active_ingredient": m.get("active_ingredient"),
                "dosage_frequency": m.get("dosage_frequency"),
                "weekdays": m.get("weekdays", []),
                "times": m.get("times", []),
                "is_primary": m.get("is_primary", False),
                "ai_instruction": m.get("ai_instruction") # ✅ حفظ النصيحة
            }
            rows.append(row)
            
        # ✅ استخدام upsert بدلاً من insert لتحديث الموجود وإضافة الجديد
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
        existing_primary_times = []
        for med in existing_meds:
            if med.get("is_primary"):
                existing_primary_times.extend(med.get("times", []))

        suggestions = []
        explanation_parts = []

        for med in new_medications:
            if med.get("is_primary"):
                disease = p.get("diseases", ["default"])[0]
                result = await suggest_primary_schedule(
                    disease=disease,
                    wake_time=p["wake_time"],
                    sleep_time=p["sleep_time"],
                    dosage_frequency=med["dosage_frequency"],
                    existing_meds=existing_meds
                )
                explanation_parts.append(f"Primary {med['name']}: scheduled based on {disease}.")
            else:
                result = await suggest_secondary_schedule(
                    dosage_frequency=med["dosage_frequency"],
                    wake_time=p["wake_time"],
                    sleep_time=p["sleep_time"],
                    existing_primary_times=existing_primary_times
                )
                explanation_parts.append(f"Secondary {med['name']}: distributed to avoid conflicts.")
            suggestions.append({
                "name": med["name"],
                "active_ingredient": med.get("active_ingredient"),
                "dosage_frequency": med["dosage_frequency"],
                "weekdays": result["weekdays"],
                "times": result["times"],
                "is_primary": med.get("is_primary", False),
            })

        return {
            "type": "primary" if new_medications[0].get("is_primary") else "secondary",
            "explanation": " ".join(explanation_parts),
            "suggestions": suggestions,
        }

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