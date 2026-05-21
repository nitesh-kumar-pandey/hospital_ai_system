"""
Database services using SQLite for local/dev.
Replace with PostgreSQl in production by changing Engine_URL.
"""

import sqlite3
import os 
import threading
from datetime import datetime

DB_Path = os.environ.get("DB_PATH", "hospital.db")
_lock = threading.Lock()

# ── Resource pool defaults ──────────────────────────────────────────────────
DEFAULT_ICU_BEDS = [f"ICU-{i}" for i in range(1,6)]
DEFAULT_GENERAL_BEDS = [f"GEN-{i}" for i in range(1,21)]
DEFAULT_DOCTORS = [
     "Dr. Sharma","Dr. Patel","Dr. Mehta","Dr. Khan","Dr. Iyer","Dr. Rao",
]



def get_connection():
     conn = sqlite3.connect(DB_Path, check_same_thread=False)
     conn.row_factory = sqlite3.Row
     return conn


def init_db():
     """Create tables and seed initial data. """
     conn = get_connection()
     c = conn.cursor()

     c.executescript("""
          CREATE TABLE IF NOT EXISTS beds(
               bed_id TEXT PRIMARY KEY,
               bed_type TEXT NOT NULL,
               occupied INTEGER DEFAULT 0,
               patient_id TEXT
          );
                     
          CREATE TABLE IF NOT EXISTS doctors(
               doctor_id TEXT PRIMARY KEY,
               name TEXT NOT NULL,
               busy INTEGER DEFAULT 0,
               patient_id TEXT
          );
          
          CREATE TABLE IF NOT EXISTS patients(
               patient_id TEXT PRIMARY KEY,
               patient_name TEXT,
               age INTEGER,
               symptoms TEXT,
               vitals TEXT,
               priority_level TEXT,
               priority_score INTEGER,
               priority_reasoning TEXT,
               assigned_bed TEXT,
               assigned_doctor TEXT,
               estimated_wait_minutes INTEGER,
               status TEXT,
               timestamp TEXT,      
          );
     """)

     #Seed beds if empty
     existing = c.execute("SELECT COUNT(*) FROM beds").fetchone()[0]
     if existing == 0:
          for bed in DEFAULT_ICU_BEDS:
               c.execute("INSERT OR IGNORE INTO beds VALUES(?,'icu',0,Null)",(bed,))
          for bed in DEFAULT_GENERAL_BEDS:
               c.execute("INSERT OR IGNORE INTO beds VALUES(?,'general', 0,Null)",(bed,))
          for doc in DEFAULT_DOCTORS:
               c.execute("INSERT OR IGNORE INTO doctors VALUES (?, ?, 0, NULL)", (doc, doc))
     
     conn.commit()
     conn.close()


def get_resource_snapshot() -> dict:
     conn = get_connection()
     c = conn.cursor()
     icu = c.execute("SELECT COUNT(*) FROM beds WHERE bed_type='icu' AND occupied=0").fetchone()[0]
     gen = c.execute("SELECT COUNT(*) FROM beds WHERE bed_type='general' AND occupied=0").fetchone()[0]
     docs = c.execute("SELECT COUNT(*) FROM doctors WHERE busy=0").fetchone()[0]
     conn.close()
     return {"icu_beds": icu, "general_beds":gen, "doctors":docs}


def allocate_resource(bed_type:str) -> tuple:
     """Automatically assign a bed and doctor. Returns (bed_id, doctor_name)."""
     with _lock:
          conn = get_connection()
          c = conn.cursor()

          bed = c.execute(
               "SELECT bed_id FROM beds WHERE bed_types=? AND occupied=0 LIMIT 1",
               (bed_type,)
          ).fetchone()

          doctor = c.execute(
               "SELECT doctor_id FROM doctors WHERE busy=0 LIMIT 1"
          ).fetchone()

          bed_id = bed["bed_id"] if bed else None
          doc_id = doctor["doctor_id"] if doctor else "On-call Physician"

          if bed_id:
               c.execute("UPDATE beds SET occupied=1 WHERE bed_id=?",(bed_id,))
          if doctor:
               c.execute("UPDATE doctors SET bsuy=1 WHERE doctor_id=?", (doc_id,))

          conn.commit()
          conn.close()
          return(bed_id, doc_id)
     

def release_resource(bed_id: str, doctor_id: str):
     """Free up bed and doctor after patient discharge."""
     with _lock:
          conn = get_connection()
          c = conn.cursor()
          if bed_id:
               c.execute("UPDATE beds SET occupied=0, patient_id=NULL WHERE bed_id=?",(bed_id,))
          if doctor_id:
               c.execute("UPDATE doctors SET busy=0, patiend_id_NULL WHERE doctor_id=?",(doctor_id,))
          conn.commit()
          conn.close()


def save_patient(state:dict):
     """persist final patient state to DB."""
     import json
     conn = get_connection()
     c = conn.cursor()
     c.execute("""
          INSERT OR REPLACE INTO patients VALUES (
               ?,?,?,?,?,?,?,?,?,?,?,?,?
          )
     """,(
          state.get("patient_id"),
          state.get("patient_name"),
          state.get("age"),
          state.get("symptoms"),
          json.dumps(state.get("vitals",{})),
          state.get("priority_level"),
          state.get("priority_score"),
          state.get("priority_reasoning"),
          state.get("assigned_bed"),
          state.get("assigned_doctor"),
          state.get("estimated_wait_minutes"),
          state.get("status"),
          state.get("timestamp"),
     ))
     conn.commit()
     conn.close()


def get_all_patients() -> list:
     import json
     conn = get_connection()
     c = conn.cursor()
     rows = c.execute(
          "SELECT * FROM patients ORDER BY timestamp DESC"
     ).fetchall()
     conn.close()
     result = []
     for row in rows:
          d = dict(row)
          d["vitals"] = json.loads(d.get("vitals") or "{}")
          result.append(d)
     return result


def discharge_patient(patient_id:str):
     conn = get_connection()
     c = conn.cursor()
     row = c.execute("SELECT assigned_bed, assigned_doctor FROM patients WHERE patient_id=?",(patient_id,)).fetchone()
     if row:
          release_resource(row["assigned_bed"],row["assigned_doctor"])
          c.execute("UPDATE patients SET status='Discharged', assigned_bed = NULL,assigned_doctor = NULL WHERE patient_id=?",(patient_id,))
     conn.commit()
     conn.close()


def reset_resources():
     """Dev utility: reset all beds and doctors."""
     conn = get_connection()
     c = conn.cursor()
     c.execute("UPDATE beds SET occupied=0, patient_id=NULL")
     c.execute("UPDATE doctors SET busy=0, patient_id=NULL")
     conn.commit()
     conn.close()
