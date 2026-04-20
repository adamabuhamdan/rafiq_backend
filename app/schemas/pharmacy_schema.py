"""
Pharmacy Schemas — unified for camera, schedule buttons, and saving.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


# ── Save Medications (Add button / Save Schedule button) ──────────────────────

class MedicationSaveEntry(BaseModel):
    """A single medication ready to be persisted."""
    id: str
    name: str
    active_ingredient: Optional[str] = None
    dosage_frequency: str = Field(..., description="e.g. 'حبة يومياً', 'حبتين بالاسبوع', 'نصف حبة صباحاً ومساءً'")
    weekdays: List[str] = []          # e.g. ["sun","mon",...] - empty if not set yet
    times: List[str] = []             # HH:MM strings - empty if not set yet
    is_primary: bool = False
    ai_instruction: Optional[str] = None


class SaveMedicationsRequest(BaseModel):
    patient_id: str
    medications: List[MedicationSaveEntry]


class SaveMedicationsResponse(BaseModel):
    saved_count: int
    message: str


# ── Prescription Scan (Camera button) ─────────────────────────────────────────

class PrescriptionScanRequest(BaseModel):
    patient_id: str
    image_base64: str
    media_type: str = "image/jpeg"


class ExtractedMedication(BaseModel):
    name: str
    active_ingredient: Optional[str] = None


class PrescriptionScanResponse(BaseModel):
    extracted: List[ExtractedMedication]
    note: str


# ── Smart Schedule Suggestion (Primary / Secondary buttons) ───────────────────

class NewMedicationForSuggestion(BaseModel):
    """Medication that needs scheduling (no weekdays/times yet)."""
    id: Optional[str] = None
    name: str
    active_ingredient: Optional[str] = None
    dosage_frequency: str
    is_primary: bool


class ScheduleSuggestRequest(BaseModel):
    patient_id: str
    new_medications: List[NewMedicationForSuggestion]
    # optional: pass existing meds if frontend wants to override, otherwise backend fetches


class SuggestedMedication(BaseModel):
    id: Optional[str] = None
    name: str
    active_ingredient: Optional[str] = None
    dosage_frequency: str
    weekdays: List[str]
    times: List[str]
    is_primary: bool
    ai_instruction: Optional[str] = None


class ScheduleSuggestResponse(BaseModel):
    type: str          # "primary" or "secondary"
    explanation: str
    suggestions: List[SuggestedMedication]


# ── Interaction Check ─────────────────────────────────────────────────────────

class MedicationEntry(BaseModel):
    name: str
    active_ingredient: Optional[str] = None


class InteractionCheckRequest(BaseModel):
    medications: List[MedicationEntry]


class InteractionItem(BaseModel):
    drugs: List[Optional[str]] = []
    severity: str
    description: str


class InteractionCheckResponse(BaseModel):
    status: str
    summary: str
    interactions: List[InteractionItem] = []