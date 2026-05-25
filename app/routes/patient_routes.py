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
from app.services.report_service    import process_medical_report
from app.services.explain_service   import generate_xai_explanation
from app.services.smart_doctor_service import smart_allocate_doctor
from app.services.email_service     import send_doctor_notification_email
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


# ── Patient Admission (main flow) ──────────────────────────────────────────

@router.post("/allocate", response_model=ALLocationResponse)
async def allocation_patient(request: PatientAdmitRequest):
    """
    Admit a patient and run the full AI pipeline:
      1. LangGraph triage (intake → priority → resource → optimizer)
      2. Save patient to DB
      3. Smart doctor allocation (specialty-matched)
      4. Send email notification to assigned doctor
    """
    # ── Step 1: Triage ─────────────────────────────────────────────────
    try:
        graph       = get_graph()
        input_state = request.dict()
        logger.info(f"Admitting patient: {request.patient_name}")
        result      = graph.invoke(input_state)
        save_patient(result)
        logger.info(
            f"Patient {result['patient_id']} triaged → "
            f"{result.get('status')} | Priority: {result.get('priority_level')}"
        )
    except Exception as e:
        logger.error(f"Triage/allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # ── Step 2: Smart doctor allocation ────────────────────────────────
    # We run this separately from the LangGraph optimizer so we can get
    # the full doctor profile (including email) back.
    email_status = {"sent": False, "message": "Not attempted"}
    try:
        sd = smart_allocate_doctor(
            patient_id=result["patient_id"],
            symptoms=request.symptoms,
            priority_level=result.get("priority_level", "Medium"),
            age=request.age,
            predicted_condition=None,   # XAI runs client-side after this call
            vitals=dict(request.vitals),
            auto_assign=True,
        )

        # Propagate the smart-allocated doctor back onto the result
        if sd.get("assigned_doctor"):
            result["assigned_doctor"] = sd["assigned_doctor"]
            result["doctor_email"]    = sd.get("doctor_email", "")
            result["doctor_spec"]     = sd.get("specialization", "")
            result["match_score"]     = sd.get("match_score", 0)
            result["match_reason"]    = sd.get("match_reason", "")

        # ── Step 3: Email notification ──────────────────────────────────
        doctor_name  = sd.get("assigned_doctor")
        doctor_email = sd.get("doctor_email", "")

        if doctor_name and doctor_email:
            patient_data = {
                "patient_id":   result.get("patient_id"),
                "patient_name": request.patient_name,
                "age":          request.age,
                "symptoms":     request.symptoms,
                "vitals":       dict(request.vitals),
            }
            triage_data = {
                "priority_level":      result.get("priority_level"),
                "priority_score":      result.get("priority_score"),
                "priority_reasoning":  result.get("priority_reasoning"),
                "predicted_condition": None,   # not available yet at this stage
                "specialization":      sd.get("specialization"),
                "match_reason":        sd.get("match_reason"),
            }
            email_result = send_doctor_notification_email(
                doctor_email=doctor_email,
                doctor_name=doctor_name,
                patient_data=patient_data,
                triage_result=triage_data,
            )
            email_status = {
                "sent":    email_result["success"],
                "message": email_result["message"],
            }
            if email_result["success"]:
                logger.info(f"Doctor email sent: {email_result['message']}")
            else:
                logger.warning(f"Doctor email failed: {email_result['message']}")
        elif doctor_name and not doctor_email:
            email_status = {
                "sent":    False,
                "message": f"No email on record for {doctor_name}. Configure doctor emails in the database.",
            }
            logger.warning(email_status["message"])
        else:
            email_status = {
                "sent":    False,
                "message": sd.get("error") or "No doctor assigned — email not sent.",
            }
            logger.warning(email_status["message"])

    except Exception as exc:
        # Email / smart-doctor errors must NEVER crash the admission
        logger.error(f"Smart doctor / email step error: {exc}")
        email_status = {"sent": False, "message": f"Internal error: {exc}"}

    # Attach email status to result so Streamlit can surface it
    result["email_status"] = email_status
    return result


# ── Standard endpoints ─────────────────────────────────────────────────────

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
        raise HTTPException(
            status_code=404,
            detail="No doctor available or patient not found",
        )
    return {
        "patient_id":      patient_id,
        "assigned_doctor": doctor,
        "message":         "Doctor assigned successfully",
    }


@router.get("/resources")
async def resources():
    """Current resource availability."""
    return get_resource_snapshot()


# ── Medical Report Summarisation ───────────────────────────────────────────

@router.post("/report/summarise", response_model=ReportSummaryResponse)
async def summarise_report(file: UploadFile = File(...)):
    """Upload a medical report (PDF / image / txt) and get a structured summary."""
    if file.content_type not in ALLOWED_REPORT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                "Allowed: PDF, PNG, JPG, BMP, TIFF, WEBP, TXT"
            ),
        )
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum: 10 MB.")

    logger.info(f"Processing report: {file.filename} ({len(file_bytes)} bytes)")
    result = process_medical_report(file_bytes, file.filename)

    if result.get("error") and not result.get("raw_text"):
        raise HTTPException(status_code=422, detail=result["error"])

    return result


# ── Explainable AI ─────────────────────────────────────────────────────────

@router.post("/explain", response_model=ExplainResponse)
async def explain_prediction(request: ExplainRequest):
    """Return factor-by-factor XAI breakdown of an AI priority decision."""
    try:
        return generate_xai_explanation(
            symptoms=request.symptoms,
            vitals=request.vitals,
            age=request.age,
            priority_level=request.priority_level or "Unknown",
            priority_score=request.priority_score or 50,
        )
    except Exception as e:
        logger.error(f"XAI error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Smart Doctor (explicit API — used by Queue page "Assign Doctor" btn) ───

@router.post("/smart-doctor", response_model=SmartDoctorResponse)
async def smart_doctor_allocation(request: SmartDoctorRequest):
    """Explicit smart doctor allocation endpoint (used by manual assignment)."""
    try:
        return smart_allocate_doctor(
            patient_id=request.patient_id,
            symptoms=request.symptoms,
            priority_level=request.priority_level,
            age=request.age,
            predicted_condition=request.predicted_condition,
            vitals=request.vitals,
            auto_assign=True,
        )
    except Exception as e:
        logger.error(f"Smart doctor error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-doctor/recommend/{patient_id}")
async def recommend_doctor_for_existing_patient(patient_id: str):
    """Smart-allocate a doctor to an already-admitted patient."""
    patients = get_all_patients()
    patient  = next((p for p in patients if p["patient_id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found.")

    return smart_allocate_doctor(
        patient_id=patient_id,
        symptoms=patient.get("symptoms", ""),
        priority_level=patient.get("priority_level", "Medium"),
        age=patient.get("age", 40),
        predicted_condition=None,
        vitals=patient.get("vitals", {}),
        auto_assign=True,
    )