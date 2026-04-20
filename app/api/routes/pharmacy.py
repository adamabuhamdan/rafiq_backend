"""
Pharmacy Routes — unified for medications CRUD, camera, schedule suggestions, interactions.
"""
from fastapi import APIRouter, HTTPException, Header, status
from typing import Optional, List
from app.schemas.pharmacy_schema import (
    SaveMedicationsRequest, SaveMedicationsResponse,
    PrescriptionScanRequest, PrescriptionScanResponse, ExtractedMedication,
    ScheduleSuggestRequest, ScheduleSuggestResponse,
    InteractionCheckRequest, InteractionCheckResponse, InteractionItem,
    NewMedicationForSuggestion, SuggestedMedication,
)
from app.schemas.med_schema import MedResponse  # فقط للـ GET (قراءة)
from app.agents.functional.pharmacy_agent import PharmacyAgent
from app.db.supabase_client import get_supabase, get_user_id_from_token

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy - الصيدلة"])
pharmacy_agent = PharmacyAgent()


# ========== Save medications (direct, no AI) ==========
# ========== Save medications (direct, no AI) ==========
@router.post("/save-medications", response_model=SaveMedicationsResponse)
async def save_medications(payload: SaveMedicationsRequest):
    """إضافة دواء واحد أو أكثر (بدون AI)"""
    result = await pharmacy_agent.save_medications(
        patient_id=payload.patient_id,
        medications=[m.model_dump() for m in payload.medications],
    )
    return SaveMedicationsResponse(
        saved_count=result["saved_count"],
        message=f"تم حفظ {result['saved_count']} دواء بنجاح.",
    )

# ========== Camera scan ==========
@router.post("/scan-prescription", response_model=PrescriptionScanResponse)
async def scan_prescription(payload: PrescriptionScanRequest):
    """كاميرا: استخراج معلومات الدواء من الصورة"""
    try:
        result = await pharmacy_agent.scan_prescription(
            patient_id=payload.patient_id,
            image_base64=payload.image_base64,
            media_type=payload.media_type,
        )
        return PrescriptionScanResponse(
            extracted=[ExtractedMedication(**m) for m in result["extracted"]],
            note=result["note"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========== Smart schedule suggestion (Primary / Secondary) ==========
@router.post("/suggest-schedule", response_model=ScheduleSuggestResponse)
async def suggest_schedule(payload: ScheduleSuggestRequest):
    """اقتراح مواعيد للأدوية الجديدة (أساسي/ثانوي)"""
    try:
        result = await pharmacy_agent.suggest_smart_schedule(
            patient_id=payload.patient_id,
            new_medications=[m.model_dump() for m in payload.new_medications],
        )
        return ScheduleSuggestResponse(
            type=result["type"],
            explanation=result["explanation"],
            suggestions=[SuggestedMedication(**s) for s in result["suggestions"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========== Interaction check ==========
@router.post("/check-interactions", response_model=InteractionCheckResponse)
async def check_interactions(payload: InteractionCheckRequest):
    """فحص التفاعلات الدوائية"""
    medications = [{"name": m.name, "active_ingredient": m.active_ingredient} for m in payload.medications]
    result = await pharmacy_agent.check_interactions(medications)
    return InteractionCheckResponse(
        status=result.get("status", "safe"),
        summary=result.get("summary", ""),
        interactions=[InteractionItem(**i) for i in result.get("interactions", [])],
    )


# ========== Read & Delete endpoints (kept for compatibility) ==========
@router.get("/medications/{patient_id}", response_model=List[MedResponse])
async def get_patient_medications(patient_id: str):
    """جلب جميع أدوية المريض"""
    supabase = get_supabase()
    result = supabase.table("medications").select("*").eq("patient_id", patient_id).execute()
    return result.data


@router.delete("/medications/{patient_id}/{med_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(patient_id: str, med_id: str):
    """حذف دواء معين"""
    supabase = get_supabase()
    supabase.table("medications").delete().eq("id", med_id).eq("patient_id", patient_id).execute()