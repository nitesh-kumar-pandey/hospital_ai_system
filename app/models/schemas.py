from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class VitalsSchema(BaseModel):
     heart_rate: Optional[int] = Field(None, example=90)
     systolic_bp: Optional[int] = Field(None, example=120)
     diastolic_bp: Optional[int] = Field(None, example=80)
     temprature: Optional[int] = Field(None, example=98.6)
     spo2: Optional[int] = Field(None, example=97)
     respiratory_rate: Optional[int] = Field(None, example=16)


class PatientAdmitRequest(BaseModel):
     patient_name: str = Field(..., example="John Doe")
     age: int = Field(...,example=45)
     symptoms : str = Field(..., example="Chest pain and shortness of breath")
     vitals: Dict[str,Any] = Field(...,example={
          "heart_rate": 110,
          "systolic_bp": 160,
          "spo2": 94,
          "temprature": 99.1
     })


class ALLocationResponse(BaseModel):
     patient_id: str
     patient_name: Optional[str]
     priority_level: Optional[str]
     priority_score: Optional[int]
     priority_reasoning: Optional[str]
     assigned_bed: Optional[str]
     assigned_doctor: Optional[str]
     estimated_wait_minutes: Optional[int]
     status: Optional[str]
     timestamp: Optional[str]
     errors: Optional[list]