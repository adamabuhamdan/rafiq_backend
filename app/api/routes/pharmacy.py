"""
Pharmacy Routes — unified for medications CRUD, camera, schedule suggestions, interactions.
"""
from fastapi import APIRouter, HTTPException, Header, status
from typing import Optional, List
from datetime import datetime, timedelta, time
from app.schemas.pharmacy_schema import (
    SaveMedicationsRequest, SaveMedicationsResponse,
    PrescriptionScanRequest, PrescriptionScanResponse, ExtractedMedication,
    ScheduleSuggestRequest, ScheduleSuggestResponse,
    InteractionCheckRequest, InteractionCheckResponse, InteractionItem,
    NewMedicationForSuggestion, SuggestedMedication,
    MedicationLogCreate, MedicationLogResponse
)
from app.schemas.med_schema import MedResponse
from app.agents.functional.pharmacy_agent import PharmacyAgent
from app.db.supabase_client import get_supabase, get_user_id_from_token
from app.services.notify_service import send_missed_dose_alert

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy - الصيدلة"])
pharmacy_agent = PharmacyAgent()

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


# ========== Read & Delete endpoints ==========
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


# ========== Medication Logging ==========
@router.post("/log-dose", response_model=MedicationLogResponse)
async def log_dose(
    payload: MedicationLogCreate,
    authorization: Optional[str] = Header(None)
):
    """تسجيل أخذ الدواء وتحديد الحالة (taken أو late) بناءً على وقت الجدولة"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization token required")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    now = datetime.now()
    scheduled_datetime = datetime.combine(now.date(), payload.scheduled_time)
    diff = now - scheduled_datetime
    buffer_minutes = 60
    
    if timedelta(minutes=-buffer_minutes) <= diff <= timedelta(minutes=buffer_minutes):
        status_val = "taken"
    elif diff > timedelta(minutes=buffer_minutes):
        status_val = "late"
    else:
        status_val = "taken"

    supabase = get_supabase()
    data = {
        "patient_id": user_id,
        "medication_id": str(payload.medication_id),
        "scheduled_time": payload.scheduled_time.strftime("%H:%M:%S"),
        "status": status_val,
        "taken_at": now.isoformat()
    }
    result = supabase.table("medication_logs").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to log medication dose")
    return result.data[0]


# ========== Core function for missed dose detection (used by scheduler and endpoint) ==========
async def check_missed_doses_for_patient(patient_id: str) -> dict:
    """
    Checks if a patient missed any scheduled doses for today up to the current time,
    logs them as 'missed', and sends an alert email to the family.
    """
    supabase = get_supabase()

    # If the provided ID is an email, look up the patient's UUID
    if "@" in patient_id:
        patient_record = supabase.table("patients").select("id").eq("email", patient_id).execute()
        if not patient_record.data:
            return {"status": "error", "message": "Patient not found by email"}
        patient_id = patient_record.data[0]["id"]

    now = datetime.now()

    # 1. Get medications for the patient
    meds_result = supabase.table("medications").select("*").eq("patient_id", patient_id).execute()
    if not meds_result.data:
        return {"status": "success", "message": "No medications found for patient", "missed_logged": 0}

    # 2. Get today's logs
    today_start = datetime.combine(now.date(), datetime.min.time()).isoformat()
    logs_result = (
        supabase.table("medication_logs")
        .select("*")
        .eq("patient_id", patient_id)
        .gte("taken_at", today_start)
        .execute()
    )
    today_logs = logs_result.data or []
    logged_combinations = {
        (log["medication_id"], log["scheduled_time"]) for log in today_logs
    }

    buffer_minutes = 60
    missed_count = 0

    # 3. Iterate medications and their scheduled times
    for med in meds_result.data:
        med_id = med["id"]
        med_name = med["name"]
        times = med.get("times") or []

        # Weekday check
        weekdays = med.get("weekdays") or []
        current_day = now.strftime("%a").lower()[:3]  # e.g. 'mon', 'tue'
        if weekdays and current_day not in weekdays:
            continue

        for t_str in times:
            try:
                # Expects format "HH:MM" or "HH:MM:SS"
                parts = t_str.split(":")
                h, m = int(parts[0]), int(parts[1])
                scheduled_time_obj = time(hour=h, minute=m)
                scheduled_datetime = datetime.combine(now.date(), scheduled_time_obj)
            except (ValueError, IndexError):
                continue

            t_formatted = scheduled_time_obj.strftime("%H:%M:%S")
            if (med_id, t_formatted) in logged_combinations:
                continue

            # If the scheduled time is more than buffer minutes ago -> missed
            diff = now - scheduled_datetime
            if diff > timedelta(minutes=buffer_minutes):
                # Log as missed
                log_data = {
                    "patient_id": patient_id,
                    "medication_id": med_id,
                    "scheduled_time": t_formatted,
                    "status": "missed",
                    "taken_at": now.isoformat()
                }
                supabase.table("medication_logs").insert(log_data).execute()
                missed_count += 1

                # Send email alert to family member
                patient_result = supabase.table("patients").select("full_name").eq("id", patient_id).execute()
                patient_name = patient_result.data[0].get("full_name", "Unknown Patient") if patient_result.data else "Unknown Patient"
                
                await send_missed_dose_alert(
                    patient_id=patient_id,
                    patient_name=patient_name,
                    medication_name=med_name
                )

    return {"status": "success", "message": "Checked medications.", "missed_logged": missed_count}


# ========== API endpoint to manually trigger missed dose check ==========
@router.post("/trigger-missed-doses/{patient_id}")
async def trigger_missed_doses_endpoint(patient_id: str):
    """Manually trigger missed dose detection and alerting."""
    result = await check_missed_doses_for_patient(patient_id)
    return result



@router.get("/logs/today/{patient_id}")
async def get_today_medication_logs(patient_id: str):
    """جلب سجلات الأدوية (المأخوذة والفائتة) للمريض لليوم الحالي فقط"""
    supabase = get_supabase()
    
    # تحديد بداية اليوم (الساعة 00:00:00)
    now = datetime.now()
    today_start = datetime.combine(now.date(), datetime.min.time()).isoformat()

    # جلب السجلات من الداتابيس
    result = (
        supabase.table("medication_logs")
        .select("*")
        .eq("patient_id", patient_id)
        .gte("taken_at", today_start)
        .execute()
    )
    

    return result.data or []