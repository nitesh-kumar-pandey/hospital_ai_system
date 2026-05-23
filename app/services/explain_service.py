"""
Explainable AI Service
Provides human-readable reasoning for priority/disease predictions.
Uses rule-based feature analysis + Groq LLM for plain-language explanation.
No external XAI library required (SHAP/LIME noted as optional extension).
"""

import os
import json
import re
from app.utils.logger import get_logger
from groq import Groq

logger = get_logger(__name__)
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama3-8b-8192")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ── Rule-based Feature Scoring ─────────────────────────────────────────────

def _analyse_vitals(vitals: dict) -> list:
    """
    Return a list of factor dicts for each vital sign.
    Each factor: {factor, value, impact, direction, plain_explanation}
    """
    factors = []

    hr = vitals.get("heart_rate")
    if hr is not None:
        if hr > 130 or hr < 40:
            factors.append({
                "factor": "Heart Rate",
                "value": f"{hr} bpm",
                "impact": "high",
                "direction": "increases_risk",
                "plain_explanation": f"Heart rate of {hr} bpm is dangerously {'high' if hr > 130 else 'low'}, which can indicate a serious cardiac event."
            })
        elif hr > 100 or hr < 60:
            factors.append({
                "factor": "Heart Rate",
                "value": f"{hr} bpm",
                "impact": "medium",
                "direction": "increases_risk",
                "plain_explanation": f"Heart rate of {hr} bpm is outside the normal range (60–100 bpm), warranting attention."
            })
        else:
            factors.append({
                "factor": "Heart Rate",
                "value": f"{hr} bpm",
                "impact": "low",
                "direction": "neutral",
                "plain_explanation": f"Heart rate of {hr} bpm is within the normal range."
            })

    spo2 = vitals.get("spo2")
    if spo2 is not None:
        if spo2 < 88:
            factors.append({
                "factor": "Blood Oxygen (SpO2)",
                "value": f"{spo2}%",
                "impact": "high",
                "direction": "increases_risk",
                "plain_explanation": f"Blood oxygen at {spo2}% is critically low. The body's organs are not receiving enough oxygen."
            })
        elif spo2 < 94:
            factors.append({
                "factor": "Blood Oxygen (SpO2)",
                "value": f"{spo2}%",
                "impact": "medium",
                "direction": "increases_risk",
                "plain_explanation": f"Blood oxygen at {spo2}% is below the healthy threshold of 95%. Supplemental oxygen may be needed."
            })
        else:
            factors.append({
                "factor": "Blood Oxygen (SpO2)",
                "value": f"{spo2}%",
                "impact": "low",
                "direction": "neutral",
                "plain_explanation": f"Blood oxygen level of {spo2}% is normal."
            })

    sbp = vitals.get("systolic_bp")
    dbp = vitals.get("diastolic_bp")
    if sbp is not None:
        if sbp > 180:
            factors.append({
                "factor": "Blood Pressure (Systolic)",
                "value": f"{sbp} mmHg",
                "impact": "high",
                "direction": "increases_risk",
                "plain_explanation": f"Systolic blood pressure of {sbp} mmHg is in hypertensive crisis range (>180), raising risk of stroke or heart attack."
            })
        elif sbp < 90:
            factors.append({
                "factor": "Blood Pressure (Systolic)",
                "value": f"{sbp} mmHg",
                "impact": "high",
                "direction": "increases_risk",
                "plain_explanation": f"Systolic blood pressure of {sbp} mmHg is dangerously low, which may indicate shock or severe bleeding."
            })
        elif sbp > 140:
            factors.append({
                "factor": "Blood Pressure (Systolic)",
                "value": f"{sbp} mmHg",
                "impact": "medium",
                "direction": "increases_risk",
                "plain_explanation": f"Systolic blood pressure of {sbp} mmHg is elevated (Stage 2 hypertension)."
            })
        else:
            factors.append({
                "factor": "Blood Pressure (Systolic)",
                "value": f"{sbp} mmHg",
                "impact": "low",
                "direction": "neutral",
                "plain_explanation": f"Systolic blood pressure of {sbp} mmHg is within normal range."
            })

    temp = vitals.get("temprature") or vitals.get("temperature")
    if temp is not None:
        if temp > 103:
            factors.append({
                "factor": "Body Temperature",
                "value": f"{temp}°F",
                "impact": "high",
                "direction": "increases_risk",
                "plain_explanation": f"Temperature of {temp}°F is dangerously high (hyperpyrexia), which may indicate severe infection or heatstroke."
            })
        elif temp > 100.4:
            factors.append({
                "factor": "Body Temperature",
                "value": f"{temp}°F",
                "impact": "medium",
                "direction": "increases_risk",
                "plain_explanation": f"Temperature of {temp}°F indicates a fever, suggesting possible infection."
            })
        elif temp < 96:
            factors.append({
                "factor": "Body Temperature",
                "value": f"{temp}°F",
                "impact": "medium",
                "direction": "increases_risk",
                "plain_explanation": f"Temperature of {temp}°F is below normal, which may indicate hypothermia."
            })
        else:
            factors.append({
                "factor": "Body Temperature",
                "value": f"{temp}°F",
                "impact": "low",
                "direction": "neutral",
                "plain_explanation": f"Body temperature of {temp}°F is normal."
            })

    rr = vitals.get("respiratory_rate")
    if rr is not None:
        if rr > 30 or rr < 8:
            factors.append({
                "factor": "Respiratory Rate",
                "value": f"{rr} breaths/min",
                "impact": "high",
                "direction": "increases_risk",
                "plain_explanation": f"Breathing rate of {rr}/min is {'very fast' if rr > 30 else 'dangerously slow'}, which is a sign of respiratory distress."
            })
        elif rr > 20:
            factors.append({
                "factor": "Respiratory Rate",
                "value": f"{rr} breaths/min",
                "impact": "medium",
                "direction": "increases_risk",
                "plain_explanation": f"Breathing rate of {rr}/min is slightly elevated (normal: 12–20/min)."
            })

    return factors


def _analyse_symptoms(symptoms: str) -> list:
    """Keyword-based symptom factor extraction."""
    s = symptoms.lower()
    factors = []

    critical_kw = [
        ("cardiac arrest", "Cardiac Arrest", "Patient is in cardiac arrest — immediate resuscitation required."),
        ("not breathing", "Respiratory Failure", "Patient is not breathing — airway management is critical."),
        ("unconscious", "Loss of Consciousness", "Patient is unconscious — serious neurological or cardiac event possible."),
        ("seizure", "Seizure Activity", "Active seizure detected — risk of brain injury without immediate treatment."),
        ("stroke", "Stroke Symptoms", "Stroke symptoms present — every minute without treatment causes further brain damage."),
    ]
    high_kw = [
        ("chest pain", "Chest Pain", "Chest pain is a key warning sign for heart attack or other cardiac conditions."),
        ("difficulty breathing", "Breathing Difficulty", "Difficulty breathing can indicate lung or heart problems requiring urgent care."),
        ("shortness of breath", "Shortness of Breath", "Shortness of breath may indicate heart failure, asthma, or pulmonary embolism."),
        ("severe bleeding", "Severe Bleeding", "Uncontrolled bleeding can lead to shock and organ failure if not stopped quickly."),
        ("head injury", "Head Injury", "Head injuries carry risk of brain bleed or concussion."),
    ]
    medium_kw = [
        ("fever", "Fever", "Fever indicates the body is fighting an infection."),
        ("fracture", "Possible Fracture", "Fractures need imaging and may require surgical intervention."),
        ("vomiting", "Vomiting", "Persistent vomiting may indicate GI issues or raised intracranial pressure."),
        ("dizziness", "Dizziness", "Dizziness can be linked to low blood pressure, inner ear, or neurological causes."),
    ]

    for kw, label, explanation in critical_kw:
        if kw in s:
            factors.append({
                "factor": f"Symptom: {label}",
                "value": kw,
                "impact": "high",
                "direction": "increases_risk",
                "plain_explanation": explanation,
            })

    for kw, label, explanation in high_kw:
        if kw in s:
            factors.append({
                "factor": f"Symptom: {label}",
                "value": kw,
                "impact": "medium",
                "direction": "increases_risk",
                "plain_explanation": explanation,
            })

    for kw, label, explanation in medium_kw:
        if kw in s:
            factors.append({
                "factor": f"Symptom: {label}",
                "value": kw,
                "impact": "low",
                "direction": "increases_risk",
                "plain_explanation": explanation,
            })

    return factors


def _analyse_age(age: int) -> dict:
    if age >= 75:
        return {
            "factor": "Age",
            "value": f"{age} years",
            "impact": "medium",
            "direction": "increases_risk",
            "plain_explanation": f"At {age} years, the patient is elderly. Older patients are at higher risk for complications and typically need closer monitoring.",
        }
    elif age <= 2:
        return {
            "factor": "Age",
            "value": f"{age} years",
            "impact": "medium",
            "direction": "increases_risk",
            "plain_explanation": f"Patient is {age} years old (infant/toddler). Young children require specialist paediatric care.",
        }
    else:
        return {
            "factor": "Age",
            "value": f"{age} years",
            "impact": "low",
            "direction": "neutral",
            "plain_explanation": f"Patient's age of {age} years is not an elevated risk factor by itself.",
        }


# ── LLM Plain-language Summary ─────────────────────────────────────────────

XAI_PROMPT = """You are a medical AI that explains clinical decisions in simple language.

Patient details:
- Age: {age}
- Symptoms: {symptoms}
- Vitals: {vitals}
- AI assigned Priority: {priority_level} (score: {priority_score}/100)

Top risk factors identified:
{factors_text}

Write a SHORT, clear explanation (3-4 sentences) that:
1. States the predicted priority/condition in plain English
2. Names the 2-3 most important contributing factors
3. Tells the patient/doctor what this means for next steps

Respond ONLY with a JSON object:
{{"predicted_condition": "<most likely condition/concern>",
  "confidence": "High|Medium|Low",
  "plain_summary": "<3-4 sentence plain English explanation>",
  "clinical_note": "<one sentence for the doctor>"
}}"""


def generate_xai_explanation(
    symptoms: str,
    vitals: dict,
    age: int,
    priority_level: str = "Unknown",
    priority_score: int = 50
) -> dict:
    """
    Main XAI function. Returns structured explanation with top factors.
    """
    # 1. Rule-based factor extraction
    vital_factors  = _analyse_vitals(vitals)
    symptom_factors = _analyse_symptoms(symptoms)
    age_factor     = _analyse_age(age)

    all_factors = symptom_factors + vital_factors + [age_factor]

    # Sort: high → medium → low
    order = {"high": 0, "medium": 1, "low": 2}
    all_factors.sort(key=lambda x: order.get(x.get("impact", "low"), 3))

    # Top 5 for display
    top_factors = all_factors[:5]

    # 2. LLM plain summary
    factors_text = "\n".join(
        f"- {f['factor']} ({f['value']}): {f['plain_explanation']}"
        for f in top_factors
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": XAI_PROMPT.format(
                age=age,
                symptoms=symptoms,
                vitals=json.dumps(vitals),
                priority_level=priority_level,
                priority_score=priority_score,
                factors_text=factors_text,
            )}],
            temperature=0.1,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        llm_out = json.loads(match.group()) if match else {}
    except Exception as e:
        logger.warning(f"XAI LLM failed, using fallback: {e}")
        llm_out = {}

    return {
        "predicted_condition": llm_out.get("predicted_condition", _infer_condition(symptoms, vitals)),
        "confidence": llm_out.get("confidence", "Medium"),
        "priority_level": priority_level,
        "top_factors": top_factors,
        "plain_summary": llm_out.get(
            "plain_summary",
            f"Based on the patient's symptoms and vitals, the AI assessed a {priority_level} priority level. "
            f"Key contributing factors include: {', '.join(f['factor'] for f in top_factors[:3])}."
        ),
        "clinical_note": llm_out.get("clinical_note", "Verify with clinical assessment."),
    }


def _infer_condition(symptoms: str, vitals: dict) -> str:
    s = symptoms.lower()
    if "chest pain" in s or "shortness of breath" in s:
        return "Possible Acute Coronary Syndrome / Cardiac Event"
    if "seizure" in s or "unconscious" in s:
        return "Neurological Emergency"
    if "fever" in s or vitals.get("temprature", 98) > 100.4:
        return "Infectious / Inflammatory Condition"
    if "fracture" in s or "injury" in s:
        return "Traumatic Injury"
    return "Undifferentiated — Requires Clinical Evaluation"
