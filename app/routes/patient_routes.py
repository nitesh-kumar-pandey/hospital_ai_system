from fastapi import APIRouter, HTTPException
from app.models.schemas import PatientAdmitRequest, ALLocationResponse
from app.graph.workflow import get_graph
from app.services.db_services import save_patient, get_all_patients,discharge_patient, get_resource_snapshot,assign_doctor_to_patient
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1", tags=["patients"])
logger = get_logger(__name__)


@router.post("/allocate", response_model=ALLocationResponse)
async def allocation_patient(request: PatientAdmitRequest):
     """Admit a patient and run ai triage + resource allocation """
     try:
          graph = get_graph()
          input_state = request.dict()
          logger.info(f"Admitting patient: {request.patient_name}")
          result = graph.invoke(input_state)
          save_patient(result)
          logger.info(f"Patient {result['patient_id']} → {result.get('status')} | Priority: {result.get('priority_level')}")
          return result
     except Exception as e:
          logger.error(f"Allocation error : {e}")
          raise HTTPException(status_code=500,detail=str(e))
     

@router.get("/patients")
async def list_patients():
     """List all patients"""
     return get_all_patients()


@router.post("/discharge/{patient_id}")
async def discharge(patient_id: str):
     """Discharge a patient and free resources."""
     discharge_patient(patient_id)
     return {"message": f"Patient {patient_id} discharged successfully."}

@router.post("/assign-doctor/{patient_id}")
def assign_doctor(patient_id: str):
    doctor = assign_doctor_to_patient(patient_id)

    if not doctor:
        raise HTTPException(status_code=404, detail="No doctor available or patient not found")

    return {
        "patient_id": patient_id,
        "assigned_doctor": doctor,
        "message": "Doctor assigned successfully"
    }

@router.get("/resources")
async def resources():
     """Current resource availability. """
     return get_resource_snapshot()