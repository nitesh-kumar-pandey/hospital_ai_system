from fastapi import APIRouter, HTTPException, UploadFile, File
from app.models.schemas import (
    PatientAdmitRequest, ALLocationResponse,
    ReportSummaryResponse, ExplainRequest, ExplainResponse,
    SmartDoctorRequest, SmartDoctorResponse,
)
from app.graph.workflow import get_graph
from app.services.db_services import (
    save_patient, get_all_patients, discharge_patient,
    get_resource_snapshot, assign_doctor_to_patient,
)
from app.services.report_service import process_medical_report
from app.services.explain_service import generate_xai_explanation
from app.services.smart_doctor_service import smart_allocate_doctor
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1", tags=["patients"])
logger = get_logger(__name__)

ALLOWED_REPORT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/bmp",
    "image/tiff",
    "image/webp",
    "text/plain",
}


# ── Existing Endpoints ─────────────────────────────────────────────────────

@router.post("/allocate", response_model=ALLocationResponse)
async def allocation_patient(request: PatientAdmitRequest):
    """Admit a patient and run AI triage + resource allocation."""
    try:
        graph = get_graph()
        input_state = request.dict()
        logger.info(f"Admitting patient: {request.patient_name}")
        result = graph.invoke(input_state)
        save_patient(result)
        logger.info(
            f"Patient {result['patient_id']} → {result.get('status')} | Priority: {result.get('priority_level')}"
        )
        return result
    except Exception as e:
        logger.error(f"Allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients")
async def list_patients():
    """List all patients."""
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
        "message": "Doctor assigned successfully",
    }


@router.get("/resources")
async def resources():
    """Current resource availability."""
    return get_resource_snapshot()


# ── Feature 1: Medical Report Summarisation ────────────────────────────────

@router.post("/report/summarise", response_model=ReportSummaryResponse)
async def summarise_report(file: UploadFile = File(...)):
    """
    Upload a medical report (PDF, image, or .txt).
    Returns a structured, patient-friendly summary with diagnosis,
    medications, lab results, recommendations, and urgency flag.
    """
    # Validate content type
    if file.content_type not in ALLOWED_REPORT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                f"Allowed types: PDF, PNG, JPG, BMP, TIFF, WEBP, TXT"
            ),
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed: 10 MB.")

    logger.info(f"Processing medical report: {file.filename} ({len(file_bytes)} bytes)")

    result = process_medical_report(file_bytes, file.filename)

    if "error" in result and result.get("error") and not result.get("raw_text"):
        raise HTTPException(status_code=422, detail=result["error"])

    return result


# ── Feature 2: Explainable AI ─────────────────────────────────────────────

@router.post("/explain", response_model=ExplainResponse)
async def explain_prediction(request: ExplainRequest):
    """
    Provide an explainable breakdown of the AI's priority/disease prediction.
    Returns top contributing factors in plain language suitable for patients
    and doctors.
    """
    try:
        explanation = generate_xai_explanation(
            symptoms=request.symptoms,
            vitals=request.vitals,
            age=request.age,
            priority_level=request.priority_level or "Unknown",
            priority_score=request.priority_score or 50,
        )
        return explanation
    except Exception as e:
        logger.error(f"XAI explain error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Feature 3: Smart Doctor Allocation ────────────────────────────────────

@router.post("/smart-doctor", response_model=SmartDoctorResponse)
async def smart_doctor_allocation(request: SmartDoctorRequest):
    """
    Intelligently allocate the best available doctor to a patient based on:
    predicted condition, emergency level, doctor specialization, and experience.
    """
    try:
        result = smart_allocate_doctor(
            patient_id=request.patient_id,
            symptoms=request.symptoms,
            priority_level=request.priority_level,
            age=request.age,
            predicted_condition=request.predicted_condition,
            vitals=request.vitals,
            auto_assign=True,
        )
        return result
    except Exception as e:
        logger.error(f"Smart doctor allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-doctor/recommend/{patient_id}")
async def recommend_doctor_for_existing_patient(patient_id: str):
    """
    For an already-admitted patient: recommend and assign the best doctor
    using the patient's stored data.
    """
    patients = get_all_patients()
    patient = next((p for p in patients if p["patient_id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found.")

    result = smart_allocate_doctor(
        patient_id=patient_id,
        symptoms=patient.get("symptoms", ""),
        priority_level=patient.get("priority_level", "Medium"),
        age=patient.get("age", 40),
        predicted_condition=None,
        vitals=patient.get("vitals", {}),
        auto_assign=True,
    )
    return result