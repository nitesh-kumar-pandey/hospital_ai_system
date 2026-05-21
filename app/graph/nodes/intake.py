from datetime import datetime
import uuid 


def intake_node(state: dict) -> dict:
     """Normalize and validate incoming patient data. """

     errors =[]

     #validate required fields 
     if not state.get("symptoms"):
          errors.append("Missing symptoms")
     if not state.get("vitals"):
          errors.append("Missing vitals")

     #Assign patient ID if missing 
     if not state.get("patient_id"):
          state["patient_id"] = str(uuid.uuid4())[:8].upper()

     #normalize vitals keys to lowercase
     if state.get("vitals"):
          state["vitals"] = {k.lower(): v for k, v in state["vitals"].items()}

     #Timestamp
     state["timestamp"] = datetime.utcnow().isoformat()
     state["errors"] = errors
     state["status"] = "Registered" if not errors else "Error"

     return state