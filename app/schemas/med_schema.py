"""
Medication Schemas — aligned with the new Supabase schema.
weekdays (TEXT[])  : ['mon','tue','wed','thu','fri','sat','sun']
times    (TIME[])  : ['08:00:00', '20:00:00']
is_primary         : True = chronic medication, False = acute/temporary
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import time
from enum import Enum


class Weekday(str, Enum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


VALID_WEEKDAYS = {d.value for d in Weekday}


class MedCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    active_ingredient: Optional[str] = None
    dosage: str  # e.g. "500mg"
    weekdays: List[Weekday] = Field(..., min_length=1, description="Days to take medication")
    times: List[time] = Field(..., min_length=1, description="Times of day for each dose")
    is_primary: bool = True  # True = chronic, False = acute/temporary
    notes: Optional[str] = None

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, v: List[Weekday]) -> List[Weekday]:
        if not v:
            raise ValueError("At least one weekday must be specified")
        return v

    @field_validator("times")
    @classmethod
    def validate_times(cls, v: List[time]) -> List[time]:
        if not v:
            raise ValueError("At least one time must be specified")
        return v


class MedResponse(BaseModel):
    id: str
    patient_id: str
    name: str
    active_ingredient: Optional[str] = None
    dosage_frequency: str
    weekdays: List[str]
    times: List[str]  # Returned as strings from Supabase
    is_primary: bool
    ai_instruction: Optional[str] = None

    class Config:
        from_attributes = True


class VisionScanRequest(BaseModel):
    image_base64: str
    patient_id: str
