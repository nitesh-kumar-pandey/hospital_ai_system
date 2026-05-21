from typing  import TypedDict, Optional, List


class HospitalState(TypedDict):
     #Patient Info
     patient_id: str
     patient_name: str
     age: int
     symptoms: str
     vitals: dict

     #Priority 
     priority_score: Optional[int]
     priority_level: Optional[int]
     priority_reasoning: Optional[int]

     #Resources
     available_beds: Optional[int]
     available_doctors: Optional[int]
     available_icu_beds: Optional[int]

     #Assignment
     assigned_bed : Optional[str]
     assigned_doctor : Optional[str]
     estimated_wait_minutes: Optional[int]

     #Status
     status: Optional[str]
     errors: Optional[List[str]]
     timestamp: Optional[str]