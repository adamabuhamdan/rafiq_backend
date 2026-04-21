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
    MedicationLogCreate, MedicationLogResponse
)
from app.schemas.med_schema import MedResponse  # فقط للـ GET (قراءة)
from datetime import datetime, timedelta, date, time
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
    # Combine today's date with the scheduled time to make it comparable
    scheduled_datetime = datetime.combine(now.date(), payload.scheduled_time)
    
    # Calculate time difference
    diff = now - scheduled_datetime
    
    # Determine status based on buffer (60 mins)
    buffer_minutes = 60
    if timedelta(minutes=-buffer_minutes) <= diff <= timedelta(minutes=buffer_minutes):
        status_val = "taken"
    elif diff > timedelta(minutes=buffer_minutes):
        status_val = "late"
    else:
        # Taken too early, but let's count it as 'taken' or perhaps we just use 'taken' for early doses as well.
        status_val = "taken"

    supabase = get_supabase()
    data = {
        "patient_id": user_id,
        "medication_id": str(payload.medication_id),
        "scheduled_time": payload.scheduled_time.strftime("%H:%M:%S"),
        "status": status_val,
        # taken_at will be set by default in DB or we can pass now.isoformat()
        "taken_at": now.isoformat()
    }
    
    result = supabase.table("medication_logs").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to log medication dose")
    
    return result.data[0]

from app.services.notify_service import send_missed_dose_alert

@router.post("/trigger-missed-doses/{patient_id}")
async def check_missed_doses_for_patient(patient_id: str):
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
    current_time_str = now.strftime("%H:%M:%S")

    # 1. Query medications for the patient
    meds_result = supabase.table("medications").select("*").eq("patient_id", patient_id).execute()
    if not meds_result.data:
        return {"status": "success", "message": "No medications found for patient", "missed_logged": 0}

    # 2. Query today's logs for the patient
    # Ensure taken_at is today
    today_start = datetime.combine(now.date(), datetime.min.time()).isoformat()
    logs_result = (
        supabase.table("medication_logs")
        .select("*")
        .eq("patient_id", patient_id)
        .gte("taken_at", today_start)
        .execute()
    )
    today_logs = logs_result.data or []
    
    # Create a set of (medication_id, scheduled_time) that have been logged today
    logged_combinations = {
        (log["medication_id"], log["scheduled_time"]) for log in today_logs
    }

    missed_count = 0
    buffer_minutes = 60

    # 3. Check for missed doses
    # Wait, how are times stored in medications table? 
    # Usually in a `times` array (List[str]).
    
    for med in meds_result.data:
        med_id = med["id"]
        med_name = med["name"]
        times = med.get("times") or []
        
        # Check if the medication is scheduled for today
        # Weekdays check might be needed if they have `weekdays` array
        weekdays = med.get("weekdays") or []
        current_day = now.strftime("%a").lower()[:3] # e.g. "mon", "tue", "wed" (if that's the format used)
        
        # If weekdays array is present and today is not in it, skip
        # Note: If weekdays is empty, we assume everyday.
        if weekdays and current_day not in [day.lower()[:3] for day in weekdays]:
             # Wait, usually weekdays are ["mon", "tue"]
             # So we will just use a simple check. If format differs, we might need a more robust check.
             # In pharmacy_schema.py: weekdays: List[str] = [] # e.g. ["sun","mon",...]
             if current_day not in weekdays and current_day not in [day.lower()[:3] for day in weekdays]:
                 continue

        for t_str in times:
            # Parse time string
            try:
                # Assuming t_str is "HH:MM"
                h, m = map(int, t_str.split(":")[:2])
                scheduled_time_obj = time(hour=h, minute=m)
                scheduled_datetime = datetime.combine(now.date(), scheduled_time_obj)
            except ValueError:
                continue

            # Format to "HH:MM:SS" for comparison with logged combinations
            t_formatted = scheduled_time_obj.strftime("%H:%M:%S")
            
            # If a log exists for this med + scheduled time today, skip
            if (med_id, t_formatted) in logged_combinations:
                continue
                
            # If time has passed the buffer, it's missed
            diff = now - scheduled_datetime
            if diff > timedelta(minutes=buffer_minutes):
                # Missed!
                log_data = {
                    "patient_id": patient_id,
                    "medication_id": med_id,
                    "scheduled_time": t_formatted,
                    "status": "missed",
                    "taken_at": now.isoformat() # Logged at the time of check
                }
                supabase.table("medication_logs").insert(log_data).execute()
                missed_count += 1
                
                # Fetch patient name (for alert)
                patient_result = supabase.table("patients").select("full_name").eq("id", patient_id).single().execute()
                patient_name = patient_result.data.get("full_name", "Unknown Patient") if patient_result.data else "Unknown Patient"
                
                # Trigger alert
                await send_missed_dose_alert(
                    patient_id=patient_id,
                    patient_name=patient_name,
                    medication_name=med_name
                )
                
    return {"status": "success", "message": f"Checked medications.", "missed_logged": missed_count}