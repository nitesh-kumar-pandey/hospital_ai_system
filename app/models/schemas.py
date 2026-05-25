from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


# ── Vitals ─────────────────────────────────────────────────────────────────
class VitalsSchema(BaseModel):
    heart_rate: Optional[int] = Field(None, example=90)
    systolic_bp: Optional[int] = Field(None, example=120)
    diastolic_bp: Optional[int] = Field(None, example=80)
    temprature: Optional[float] = Field(None, example=98.6)
    spo2: Optional[int] = Field(None, example=97)
    respiratory_rate: Optional[int] = Field(None, example=16)


# ── Patient Admission ──────────────────────────────────────────────────────
class PatientAdmitRequest(BaseModel):
    patient_name: str = Field(..., example="John Doe")
    age: int = Field(..., example=45)
    symptoms: str = Field(..., example="Chest pain and shortness of breath")
    vitals: Dict[str, Any] = Field(..., example={
        "heart_rate": 110,
        "systolic_bp": 160,
        "spo2": 94,
        "temprature": 99.1
    })


# ── Allocation Response ────────────────────────────────────────────────────
class ALLocationResponse(BaseModel):
    patient_id: str
    patient_name: Optional[str] = None
    priority_level: Optional[str] = None
    priority_score: Optional[int] = None
    priority_reasoning: Optional[str] = None
    assigned_bed: Optional[str] = None
    assigned_doctor: Optional[str] = None
    estimated_wait_minutes: Optional[int] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None
    errors: Optional[list] = None

    # Smart doctor + email fields
    doctor_email: Optional[str] = None
    doctor_spec: Optional[str] = None
    match_score: Optional[int] = None
    match_reason: Optional[str] = None
    email_status: Optional[Dict[str, Any]] = None


# ── Medical Report Summary ─────────────────────────────────────────────────
class ReportSummaryResponse(BaseModel):
    """Structured response from medical report summarisation."""
    raw_text: Optional[str] = Field(None, description="Extracted raw text from the report")
    patient_name: Optional[str] = None
    age: Optional[str] = None
    diagnosis: Optional[List[str]] = Field(default_factory=list)
    symptoms: Optional[List[str]] = Field(default_factory=list)
    medications: Optional[List[str]] = Field(default_factory=list)
    lab_results: Optional[Dict[str, Any]] = Field(default_factory=dict)
    doctor_notes: Optional[str] = None
    recommendations: Optional[List[str]] = Field(default_factory=list)
    patient_friendly_summary: Optional[str] = None
    urgency_flag: Optional[str] = Field(None, description="Critical / Watch / Normal")
    error: Optional[str] = None


# ── XAI / Explainability ──────────────────────────────────────────────────
class ExplainRequest(BaseModel):
    patient_id: Optional[str] = None
    symptoms: str
    vitals: Dict[str, Any]
    age: int
    priority_level: Optional[str] = None
    priority_score: Optional[int] = None


class FeatureFactor(BaseModel):
    factor: str
    value: Any
    impact: str          # "high" | "medium" | "low"
    direction: str       # "increases_risk" | "decreases_risk" | "neutral"
    plain_explanation: str


class ExplainResponse(BaseModel):
    predicted_condition: Optional[str]
    confidence: Optional[str]
    priority_level: Optional[str]
    top_factors: List[FeatureFactor]
    plain_summary: str
    clinical_note: Optional[str]
    error: Optional[str] = None


# ── Smart Doctor Allocation ────────────────────────────────────────────────
class DoctorProfile(BaseModel):
    doctor_id: str
    name: str
    specialization: str
    experience_years: int
    busy: bool
    current_patient_count: int = 0


class SmartDoctorRequest(BaseModel):
    patient_id: str
    symptoms: str
    predicted_condition: Optional[str] = None
    priority_level: str
    age: int
    vitals: Dict[str, Any] = Field(default_factory=dict)


class SmartDoctorResponse(BaseModel):
    patient_id: str
    assigned_doctor: Optional[str]
    specialization: Optional[str]
    experience_years: Optional[int]
    match_score: Optional[int]
    match_reason: str
    fallback_used: bool = False
    error: Optional[str] = None