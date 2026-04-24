"""
Patient Routes — Manage patient medical profiles.
IMPORTANT: patient.id must equal the Supabase auth user_id (auth.users.id).
The ID comes from the Authorization token, not generated here.
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from app.schemas.patient_schema import PatientCreate, PatientUpdate, PatientResponse
from app.db.supabase_client import get_supabase, get_user_id_from_token

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(
    payload: PatientCreate,
    authorization: Optional[str] = Header(None),
):
    """
    Create a patient profile.
    The patient's id is set to the authenticated user's UUID from the JWT token,
    so RLS policies (auth.uid() = id) work correctly.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization token required")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    supabase = get_supabase()
    data = payload.model_dump()
    data["id"] = user_id  # Bind patient.id to auth.users.id
    data["date_of_birth"] = str(data["date_of_birth"])
    data["wake_time"] = str(data["wake_time"])
    data["sleep_time"] = str(data["sleep_time"])
    # Convert DiseaseType enums to plain strings
    data["diseases"] = [d.value if hasattr(d, "value") else d for d in data.get("diseases", [])]

    result = supabase.table("patients").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create patient profile")
    return result.data[0]


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str):
    supabase = get_supabase()
    result = (
        supabase.table("patients").select("*").eq("id", patient_id).execute()
    )
    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    return result.data[0]


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, payload: PatientUpdate):
    supabase = get_supabase()
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "wake_time" in data:
        data["wake_time"] = str(data["wake_time"])
    if "sleep_time" in data:
        data["sleep_time"] = str(data["sleep_time"])
    if "diseases" in data:
        data["diseases"] = [d.value if hasattr(d, "value") else d for d in data["diseases"]]

    result = supabase.table("patients").update(data).eq("id", patient_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Patient not found")
    return result.data[0]
