"""
Database services using SQLite for local/dev.
"""

import sqlite3
import os
import threading
import json
from app.utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.environ.get("DB_PATH", "hospital.db")
_lock = threading.Lock()

DEFAULT_ICU_BEDS = [f"ICU-{i}" for i in range(1, 6)]
DEFAULT_GENERAL_BEDS = [f"GEN-{i}" for i in range(1, 21)]

DEFAULT_DOCTORS = [
    ("Dr. Sharma", "Dr. Sharma", "Cardiologist", 12, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Arjun Verma", "Dr. Arjun Verma", "Cardiologist", 10, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Priya Nair", "Dr. Priya Nair", "Cardiologist", 9, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Rakesh Sinha", "Dr. Rakesh Sinha", "Cardiologist", 14, "nitesh.pandey@virtuowhiz.com"),

    ("Dr. Patel", "Dr. Patel", "General Physician", 8, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Neha Gupta", "Dr. Neha Gupta", "General Physician", 7, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Vikram Joshi", "Dr. Vikram Joshi", "General Physician", 11, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Anjali Mehra", "Dr. Anjali Mehra", "General Physician", 6, "nitesh.pandey@virtuowhiz.com"),

    ("Dr. Mehta", "Dr. Mehta", "Neurologist", 10, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Kavita Rao", "Dr. Kavita Rao", "Neurologist", 13, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Sameer Malhotra", "Dr. Sameer Malhotra", "Neurologist", 9, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Ritu Bansal", "Dr. Ritu Bansal", "Neurologist", 8, "nitesh.pandey@virtuowhiz.com"),

    ("Dr. Khan", "Dr. Khan", "Emergency Medicine", 15, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Aman Sheikh", "Dr. Aman Sheikh", "Emergency Medicine", 12, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Sneha Kapoor", "Dr. Sneha Kapoor", "Emergency Medicine", 10, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Farhan Ali", "Dr. Farhan Ali", "Emergency Medicine", 14, "nitesh.pandey@virtuowhiz.com"),

    ("Dr. Iyer", "Dr. Iyer", "Pulmonologist", 9, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Meera Thomas", "Dr. Meera Thomas", "Pulmonologist", 11, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Rohit Menon", "Dr. Rohit Menon", "Pulmonologist", 8, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Sana Qureshi", "Dr. Sana Qureshi", "Pulmonologist", 10, "nitesh.pandey@virtuowhiz.com"),

    ("Dr. Rao", "Dr. Rao", "Orthopedic Surgeon", 11, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Karan Kapoor", "Dr. Karan Kapoor", "Orthopedic Surgeon", 9, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Pooja Saxena", "Dr. Pooja Saxena", "Orthopedic Surgeon", 7, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Harsh Vardhan", "Dr. Harsh Vardhan", "Orthopedic Surgeon", 13, "nitesh.pandey@virtuowhiz.com"),

    ("Dr. Nitin Agarwal", "Dr. Nitin Agarwal", "Gastroenterologist", 10, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Shalini Bose", "Dr. Shalini Bose", "Gastroenterologist", 8, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Aditya Sen", "Dr. Aditya Sen", "Gastroenterologist", 12, "nitesh.pandey@virtuowhiz.com"),

    ("Dr. Riya Sharma", "Dr. Riya Sharma", "Pediatrician", 9, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Mohit Jain", "Dr. Mohit Jain", "Pediatrician", 7, "nitesh.pandey@virtuowhiz.com"),
    ("Dr. Ananya Das", "Dr. Ananya Das", "Pediatrician", 11, "nitesh.pandey@virtuowhiz.com"),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS beds (
            bed_id TEXT PRIMARY KEY,
            bed_type TEXT NOT NULL,
            occupied INTEGER DEFAULT 0,
            patient_id TEXT
        );

        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            specialization TEXT DEFAULT 'General Physician',
            experience_years INTEGER DEFAULT 5,
            email TEXT DEFAULT '',
            busy INTEGER DEFAULT 0,
            patient_id TEXT
        );

        CREATE TABLE IF NOT EXISTS patients (
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
            timestamp TEXT
        );
    """)

    for col_sql in [
        "ALTER TABLE doctors ADD COLUMN specialization TEXT DEFAULT 'General Physician'",
        "ALTER TABLE doctors ADD COLUMN experience_years INTEGER DEFAULT 5",
        "ALTER TABLE doctors ADD COLUMN email TEXT DEFAULT ''",
    ]:
        try:
            c.execute(col_sql)
        except Exception:
            pass

    if c.execute("SELECT COUNT(*) FROM beds").fetchone()[0] == 0:
        for bed in DEFAULT_ICU_BEDS:
            c.execute("INSERT OR IGNORE INTO beds VALUES (?, 'icu', 0, NULL)", (bed,))
        for bed in DEFAULT_GENERAL_BEDS:
            c.execute("INSERT OR IGNORE INTO beds VALUES (?, 'general', 0, NULL)", (bed,))

    for doc_id, name, spec, exp, email in DEFAULT_DOCTORS:
        c.execute("""
            INSERT OR IGNORE INTO doctors
            (doctor_id, name, specialization, experience_years, email, busy, patient_id)
            VALUES (?, ?, ?, ?, ?, 0, NULL)
        """, (doc_id, name, spec, exp, email))

        c.execute("""
            UPDATE doctors
            SET name=?, specialization=?, experience_years=?, email=?
            WHERE doctor_id=?
        """, (name, spec, exp, email, doc_id))

    conn.commit()
    conn.close()


def sync_resource_status():
    """
    Fix stale doctor/bed busy flags.
    Only active patients keep assigned doctors/beds busy.
    Discharged or removed patients release resources automatically.
    """
    with _lock:
        conn = get_connection()
        c = conn.cursor()

        c.execute("UPDATE doctors SET busy=0, patient_id=NULL")
        c.execute("UPDATE beds SET occupied=0, patient_id=NULL")

        active_rows = c.execute("""
            SELECT patient_id, assigned_bed, assigned_doctor
            FROM patients
            WHERE LOWER(COALESCE(status, '')) != 'discharged'
        """).fetchall()

        for row in active_rows:
            patient_id = row["patient_id"]
            bed_id = row["assigned_bed"]
            doctor_id = row["assigned_doctor"]

            if bed_id:
                c.execute("""
                    UPDATE beds
                    SET occupied=1, patient_id=?
                    WHERE bed_id=?
                """, (patient_id, bed_id))

            if doctor_id:
                c.execute("""
                    UPDATE doctors
                    SET busy=1, patient_id=?
                    WHERE doctor_id=?
                """, (patient_id, doctor_id))

        conn.commit()
        conn.close()


def get_resource_snapshot() -> dict:
    sync_resource_status()

    conn = get_connection()
    c = conn.cursor()

    icu = c.execute(
        "SELECT COUNT(*) FROM beds WHERE bed_type='icu' AND occupied=0"
    ).fetchone()[0]

    gen = c.execute(
        "SELECT COUNT(*) FROM beds WHERE bed_type='general' AND occupied=0"
    ).fetchone()[0]

    available_docs = c.execute(
        "SELECT COUNT(*) FROM doctors WHERE busy=0"
    ).fetchone()[0]

    total_docs = c.execute(
        "SELECT COUNT(*) FROM doctors"
    ).fetchone()[0]

    busy_docs = c.execute(
        "SELECT COUNT(*) FROM doctors WHERE busy=1"
    ).fetchone()[0]

    conn.close()

    return {
        "icu_beds": icu,
        "general_beds": gen,
        "doctors": available_docs,
        "total_doctors": total_docs,
        "busy_doctors": busy_docs,
    }


def allocate_resource(bed_type: str) -> tuple:
    sync_resource_status()

    with _lock:
        conn = get_connection()
        c = conn.cursor()

        bed = c.execute(
            "SELECT bed_id FROM beds WHERE bed_type=? AND occupied=0 LIMIT 1",
            (bed_type,)
        ).fetchone()

        doctor = c.execute(
            "SELECT doctor_id FROM doctors WHERE busy=0 LIMIT 1"
        ).fetchone()

        bed_id = bed["bed_id"] if bed else None
        doctor_id = doctor["doctor_id"] if doctor else None

        if bed_id:
            c.execute("UPDATE beds SET occupied=1 WHERE bed_id=?", (bed_id,))

        if doctor_id:
            c.execute("UPDATE doctors SET busy=1 WHERE doctor_id=?", (doctor_id,))

        conn.commit()
        conn.close()

        return bed_id, doctor_id or "On-call Physician"


def release_resource(bed_id: str, doctor_id: str):
    with _lock:
        conn = get_connection()
        c = conn.cursor()

        if bed_id:
            c.execute(
                "UPDATE beds SET occupied=0, patient_id=NULL WHERE bed_id=?",
                (bed_id,)
            )

        if doctor_id:
            c.execute(
                "UPDATE doctors SET busy=0, patient_id=NULL WHERE doctor_id=?",
                (doctor_id,)
            )

        conn.commit()
        conn.close()


def save_patient(state: dict):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        state.get("patient_id"),
        state.get("patient_name"),
        state.get("age"),
        state.get("symptoms"),
        json.dumps(state.get("vitals", {})),
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

    sync_resource_status()


def get_all_patients() -> list:
    sync_resource_status()

    conn = get_connection()
    c = conn.cursor()

    rows = c.execute(
        "SELECT * FROM patients ORDER BY timestamp DESC"
    ).fetchall()

    conn.close()

    patients = []
    for row in rows:
        data = dict(row)
        data["vitals"] = json.loads(data.get("vitals") or "{}")
        patients.append(data)

    return patients


def discharge_patient(patient_id: str):
    conn = get_connection()
    c = conn.cursor()

    row = c.execute(
        "SELECT assigned_bed, assigned_doctor FROM patients WHERE patient_id=?",
        (patient_id,)
    ).fetchone()

    if row:
        release_resource(row["assigned_bed"], row["assigned_doctor"])

        c.execute("""
            UPDATE patients
            SET status='Discharged',
                assigned_bed=NULL,
                assigned_doctor=NULL
            WHERE patient_id=?
        """, (patient_id,))

    conn.commit()
    conn.close()

    sync_resource_status()


def reset_resources():
    conn = get_connection()
    c = conn.cursor()

    c.execute("UPDATE beds SET occupied=0, patient_id=NULL")
    c.execute("UPDATE doctors SET busy=0, patient_id=NULL")
    c.execute("""
        UPDATE patients
        SET assigned_bed=NULL,
            assigned_doctor=NULL
        WHERE LOWER(COALESCE(status, '')) = 'discharged'
    """)

    conn.commit()
    conn.close()


def assign_doctor_to_patient(patient_id: str):
    sync_resource_status()

    with _lock:
        conn = get_connection()
        c = conn.cursor()

        doctor = c.execute(
            "SELECT doctor_id FROM doctors WHERE busy=0 LIMIT 1"
        ).fetchone()

        if not doctor:
            conn.close()
            return None

        doctor_id = doctor["doctor_id"]

        c.execute(
            "UPDATE doctors SET busy=1, patient_id=? WHERE doctor_id=?",
            (patient_id, doctor_id)
        )

        c.execute(
            "UPDATE patients SET assigned_doctor=? WHERE patient_id=?",
            (doctor_id, patient_id)
        )

        conn.commit()
        conn.close()

        return doctor_id


def assign_specific_doctor(patient_id: str, doctor_id: str) -> bool:
    sync_resource_status()

    with _lock:
        conn = get_connection()
        c = conn.cursor()

        doctor = c.execute(
            "SELECT busy FROM doctors WHERE doctor_id=?",
            (doctor_id,)
        ).fetchone()

        if not doctor or doctor["busy"] == 1:
            conn.close()
            return False

        c.execute(
            "UPDATE doctors SET busy=1, patient_id=? WHERE doctor_id=?",
            (patient_id, doctor_id)
        )

        c.execute(
            "UPDATE patients SET assigned_doctor=? WHERE patient_id=?",
            (doctor_id, patient_id)
        )

        conn.commit()
        conn.close()

        return True


def get_all_doctors() -> list:
    sync_resource_status()

    conn = get_connection()
    c = conn.cursor()

    rows = c.execute("SELECT * FROM doctors").fetchall()

    conn.close()
    return [dict(row) for row in rows]


def get_doctor_by_id(doctor_id: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()

    row = c.execute(
        "SELECT * FROM doctors WHERE doctor_id=?",
        (doctor_id,)
    ).fetchone()

    conn.close()
    return dict(row) if row else None