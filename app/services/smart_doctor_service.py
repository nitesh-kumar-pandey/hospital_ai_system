"""
Smart Doctor Allocation Service
Matches doctors to patients based on:
  - Predicted condition / specialty needed
  - Emergency level (priority)
  - Doctor availability
  - Doctor specialization & experience
Uses Groq LLM for specialty inference + scoring.
"""

import os
import json
import re
from app.utils.logger import get_logger
from app.services.db_services import get_all_doctors, assign_specific_doctor
from groq import Groq

logger = get_logger(__name__)
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama3-8b-8192")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ── Specialty Mapping ──────────────────────────────────────────────────────

# Maps condition keywords → preferred specialization(s)
CONDITION_SPECIALTY_MAP = [
    (["cardiac arrest", "chest pain", "heart", "myocardial", "acs", "palpitation"],
     ["Cardiologist", "Emergency Medicine"]),
    (["stroke", "seizure", "unconscious", "neuro", "brain", "headache severe", "paralysis"],
     ["Neurologist", "Emergency Medicine"]),
    (["breathing", "respiratory", "asthma", "copd", "pneumonia", "lung", "spo2"],
     ["Pulmonologist", "Emergency Medicine"]),
    (["fracture", "bone", "ortho", "joint", "ligament", "spine", "back pain"],
     ["Orthopedic Surgeon"]),
    (["fever", "infection", "sepsis", "uti", "wound", "abscess"],
     ["General Physician", "Emergency Medicine"]),
    (["trauma", "accident", "bleeding", "wound", "injury", "burn"],
     ["Emergency Medicine", "General Physician"]),
]

CRITICAL_SPECIALTIES = ["Emergency Medicine", "Cardiologist", "Neurologist"]


def _infer_needed_specialties(symptoms: str, condition: str) -> list:
    """
    Return ranked list of needed specializations based on symptoms + condition.
    """
    combined = (symptoms + " " + (condition or "")).lower()
    matched = []
    for keywords, specialties in CONDITION_SPECIALTY_MAP:
        if any(kw in combined for kw in keywords):
            matched.extend(specialties)
    # deduplicate, preserve order
    seen = set()
    result = []
    for s in matched:
        if s not in seen:
            seen.add(s)
            result.append(s)
    if not result:
        result = ["General Physician", "Emergency Medicine"]
    return result


# ── Scoring ────────────────────────────────────────────────────────────────

def _score_doctor(doctor: dict, needed_specialties: list, priority_level: str) -> int:
    """
    Score a doctor 0–100 for a given patient need.
    Higher = better match.
    """
    score = 0
    spec = doctor.get("specialization", "General Physician")
    exp  = doctor.get("experience_years", 5)
    busy = doctor.get("busy", 1)

    # Availability is hard gate — busy doctors get 0
    if busy:
        return 0

    # Specialty match
    if spec == needed_specialties[0]:
        score += 50
    elif spec in needed_specialties:
        score += 30
    elif spec == "Emergency Medicine" and priority_level in ("Critical", "High"):
        score += 35
    else:
        score += 10  # Any available doctor is better than none

    # Experience bonus (max 30 pts)
    score += min(exp * 2, 30)

    # Critical patient → prefer emergency/specialist
    if priority_level == "Critical" and spec in CRITICAL_SPECIALTIES:
        score += 20

    return min(score, 100)


# ── LLM Reasoning ─────────────────────────────────────────────────────────

DOCTOR_PROMPT = """You are a hospital triage AI that selects the best doctor for a patient.

Patient:
- Symptoms: {symptoms}
- Predicted Condition: {condition}
- Priority: {priority_level}
- Age: {age}

Available doctors:
{doctors_text}

Best matched doctor (rule-based scoring): {best_doctor}

Write ONE short sentence explaining why this doctor is the best match.
Respond ONLY in JSON: {{"reason": "<one sentence reason>"}}"""


def _get_llm_reason(
    symptoms: str, condition: str, priority_level: str, age: int,
    available_doctors: list, best_doctor: str
) -> str:
    doctors_text = "\n".join(
        f"- {d['name']} | {d['specialization']} | {d['experience_years']} yrs exp | {'Available' if not d['busy'] else 'Busy'}"
        for d in available_doctors
    )
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": DOCTOR_PROMPT.format(
                symptoms=symptoms,
                condition=condition or "Unknown",
                priority_level=priority_level,
                age=age,
                doctors_text=doctors_text,
                best_doctor=best_doctor,
            )}],
            temperature=0.1,
            max_tokens=150,
        )
        raw = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group()).get("reason", "")
    except Exception as e:
        logger.warning(f"Doctor LLM reason failed: {e}")
    return f"Assigned based on specialization match and availability for {priority_level} priority case."


# ── Public Entry Point ─────────────────────────────────────────────────────

def smart_allocate_doctor(
    patient_id: str,
    symptoms: str,
    priority_level: str,
    age: int,
    predicted_condition: str = None,
    vitals: dict = None,
    auto_assign: bool = True,
) -> dict:
    """
    Recommend (and optionally assign) the best available doctor.
    Returns a dict matching SmartDoctorResponse schema.
    """
    all_doctors = get_all_doctors()
    available   = [d for d in all_doctors if not d.get("busy")]

    if not available:
        return {
            "patient_id": patient_id,
            "assigned_doctor": None,
            "specialization": None,
            "experience_years": None,
            "match_score": 0,
            "match_reason": "No doctors are currently available. Patient placed in queue.",
            "fallback_used": True,
            "error": "All doctors are busy",
        }

    # Infer needed specialties
    needed = _infer_needed_specialties(symptoms, predicted_condition or "")

    # Score all available doctors
    scored = [
        (doc, _score_doctor(doc, needed, priority_level))
        for doc in available
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    best_doc, best_score = scored[0]

    # LLM reason
    reason = _get_llm_reason(
        symptoms=symptoms,
        condition=predicted_condition,
        priority_level=priority_level,
        age=age,
        available_doctors=available,
        best_doctor=best_doc["name"],
    )

    # Assign in DB
    assigned = False
    fallback = False
    if auto_assign:
        assigned = assign_specific_doctor(patient_id, best_doc["doctor_id"])
        if not assigned:
            # Race condition: try next best
            for doc, score in scored[1:]:
                assigned = assign_specific_doctor(patient_id, doc["doctor_id"])
                if assigned:
                    best_doc, best_score = doc, score
                    fallback = True
                    reason = f"Fallback: {best_doc['name']} assigned after first choice became unavailable."
                    break

    return {
        "patient_id": patient_id,
        "assigned_doctor": best_doc["name"] if assigned else None,
        "specialization": best_doc.get("specialization"),
        "experience_years": best_doc.get("experience_years"),
        "match_score": best_score,
        "match_reason": reason,
        "fallback_used": fallback,
        "error": None if assigned else "Doctor recommendation generated but not assigned to DB",
    }
