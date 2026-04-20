from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, time
from enum import Enum


class DiseaseType(str, Enum):
    DIABETES = "diabetes"
    HYPERTENSION = "hypertension"
    THYROID = "thyroid"


class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: date
    gender: str = Field(..., pattern="^(male|female)$")
    email: EmailStr  # Changed from phone to email
    diseases: List[DiseaseType] = []
    wake_time: time
    sleep_time: time
    medical_description: str = Field(..., description="وصف الحالة الطبية من الطبيب")
    last_test_results: Optional[str] = Field(None, description="آخر نتائج الفحوصات المخبرية (اختياري)")


class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    wake_time: Optional[time] = None
    sleep_time: Optional[time] = None
    diseases: Optional[List[DiseaseType]] = None
    medical_description: Optional[str] = None
    last_test_results: Optional[str] = None


class PatientResponse(BaseModel):
    id: str
    full_name: str
    date_of_birth: date
    gender: str
    email: str  # Changed from phone to email
    diseases: List[DiseaseType]
    wake_time: time
    sleep_time: time
    medical_description: Optional[str] = None
    last_test_results: Optional[str] = None

    class Config:
        from_attributes = True
