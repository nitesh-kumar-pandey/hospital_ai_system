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