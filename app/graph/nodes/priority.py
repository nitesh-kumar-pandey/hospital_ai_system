import json 
import re 
import os 
from groq import Groq

# Groq config 
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama3-8b-8192")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def priority_node(state: dict) -> dict:
     """Use Groq to assess patient priority from symptoms and vitals. """

     if state.get("errors"):
          return state
     
     symptoms = state.get("symptoms","")
     vitals = state.get("vitals",{})
     age = state.get("age","Unknown")

     prompt = f""" You are an emergency triage AI. Analyze the patient data below and assign a priority level.
     
Patient Age: {age}
Symptoms: {symptoms}
Vitals: {json.dumps(vitals)}

Read ONLY with a valid JSON object - no markdown, no explanation, no extra text:
{{"priority_level":"Critical|High|Medium|Low","priority_score":<1-100>,"reasoning:"<one sentence>"}}

Rules:
- Critical (85-100): life-threatening(cardiac arrest, no breathing, major trauma, SpO2<85)
- High (60-84): urgent(chest pain, difficulty breathing, severe bleeding,BP>180)
- Medium (35-59): semi-urgent(fractures, moderate pain, infection with fever)
- Low (1-34): non-urgent(minor cuts, mild cold, routine compliants)
"""
     
     try:
          response = client.chat.completions.create(
               model= GROQ_MODEL,
               messages=[{"role": "user","content":prompt}],
               temperature=0.1,
               max_tokens=200,
          )
          raw = response.choices[0].message.content.strip()

          match = re.search(r'\{.*?\}',raw, re.DOTALL)
          if not match:
               raise ValueError(f"No JSON found in response: {raw}")
          
          parsed = json.loads(match.group())

          state["priority_level"] = parsed.get("priority_level", "Medium")
          state["priority_score"] = int(parsed.get("priority_score",50))
          state["priority_reasoning"] = parsed.get("reasoning","")

     except Exception as e:
          state["priority_level"] = _rule_based_priority(vitals,symptoms)
          state["priority_score"] = _level_to_score(state["priority_level"])
          state["priority_reasoning"] = f"Rule-based fallback (LLM error: {str(e)[:100]})"
     
     state["status"] = "Triaged"
     return state


def _rule_based_priority(vitals: dict, symptoms: str) -> str:
     symptoms_lower = symptoms.lower()
     critical_kw = ["cardiac arrest", "not breathing", "unconscious", "seizure", "stroke"]
     high_kw = ["chest pain", "difficulty breathing", "severe bleeding" "head injury"]

     if any(k in symptoms_lower for k in critical_kw):
          return "Critical"
     if any(k in symptoms_lower for k in high_kw):
          return "High"
     
     hr   = vitals.get("heart_rate", 80)
     spo2 = vitals.get("spo2", 98)
     sbp  = vitals.get("systolic_bp", 120)

     if isinstance(hr,(int,float)):
          if hr > 130 or hr < 40 : return "Critical"
          if hr > 110 or hr < 50 : return "High"
     if isinstance(spo2,(int,float)) and spo2 < 90:
          return "Critical"
     if isinstance(sbp,(int,float)) and (sbp > 180 or sbp < 80):
          return "High"
     
     return "Medium"


def _level_to_score(Level:str) -> int:
     return {"Critical": 92, "High": 72, "Medium":50, "Low":20}.get(Level,50)