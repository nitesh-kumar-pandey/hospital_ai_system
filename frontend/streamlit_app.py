"""
🏥 AI Hospital Resource Allocation — Streamlit Frontend
Run: streamlit run frontend/streamlit_app.py
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime

# ── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Hospital Allocation",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE = "http://localhost:8000/api/v1"

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0f1e 0%, #0d1b2a 100%);
    border-right: 1px solid rgba(0,212,255,0.15);
}
[data-testid="stSidebar"] * { color: #e0f0ff !important; }

/* Main bg */
.stApp { background: #060d18; }

/* Priority badges */
.badge-critical { background: #ff1744; color: white; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 12px; letter-spacing: 1px; }
.badge-high { background: #ff6d00; color: white; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 12px; letter-spacing: 1px; }
.badge-medium { background: #ffd600; color: #000; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 12px; letter-spacing: 1px; }
.badge-low { background: #00e676; color: #000; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 12px; letter-spacing: 1px; }

/* Cards */
.result-card {
    background: linear-gradient(135deg, #0d1b2a, #112240);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 16px;
    padding: 24px;
    margin: 12px 0;
    box-shadow: 0 4px 24px rgba(0,212,255,0.08);
}

/* Metric panels */
.metric-box {
    background: #0d1b2a;
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.metric-number { font-size: 36px; font-weight: 700; color: #00d4ff; font-family: 'JetBrains Mono', monospace; }
.metric-label { font-size: 12px; color: #7a9bb5; letter-spacing: 1px; text-transform: uppercase; margin-top: 4px; }

/* Headers */
h1, h2, h3 { color: #e0f0ff !important; }

/* Status chips */
.status-assigned { color: #00e676; font-weight: 600; }
.status-waiting { color: #ffd600; font-weight: 600; }
.status-error { color: #ff1744; font-weight: 600; }

/* Divider */
.section-divider {
    border: none;
    border-top: 1px solid rgba(0,212,255,0.1);
    margin: 24px 0;
}

/* Patient row */
.patient-row {
    background: #0a1525;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 14px 18px;
    margin: 6px 0;
    display: flex;
    align-items: center;
    gap: 16px;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────
def priority_badge(level: str) -> str:
    cls = f"badge-{level.lower()}" if level else "badge-low"
    return f'<span class="{cls}">{level or "—"}</span>'


def get_resources():
    try:
        r = requests.get(f"{API_BASE}/resources", timeout=5)
        return r.json()
    except Exception:
        return {"icu_beds": "—", "general_beds": "—", "doctors": "—"}


def get_patients():
    try:
        r = requests.get(f"{API_BASE}/patients", timeout=5)
        return r.json()
    except Exception:
        return []


def admit_patient(data: dict):
    try:
        r = requests.post(f"{API_BASE}/allocate", json=data, timeout=30)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def discharge(pid: str):
    try:
        requests.post(f"{API_BASE}/discharge/{pid}", timeout=10)
        return True
    except Exception:
        return False


def assign_doctor(pid: str):
    try:
        r = requests.post(f"{API_BASE}/assign-doctor/{pid}", timeout=10)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500
    
# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 MediAI")
    st.markdown("**Resource Allocation System**")
    st.markdown("""
    <div style="background:#0d2a1a;border:1px solid #00e676;border-radius:8px;padding:8px 12px;margin:8px 0;font-size:12px;color:#00e676;">
        ⚡ Powered by <b>Groq</b> — Free LLM API
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["🚨 Admit Patient", "📋 Patient Queue", "📊 Dashboard"],
        label_visibility="collapsed"
    )
    st.markdown("---")

    # Groq model selector
    st.markdown("### 🤖 AI Model")
    groq_model = st.selectbox(
        "Groq Model",
        ["llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"],
        label_visibility="collapsed"
    )
    st.caption(f"Model: `{groq_model}` (free)")
    st.markdown("---")

    # Live resource panel
    st.markdown("### 🔴 Live Resources")
    res = get_resources()

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("ICU Beds", res.get("icu_beds", "—"))
        st.metric("Gen Beds", res.get("general_beds", "—"))
    with col_b:
        st.metric("Doctors", res.get("doctors", "—"))

    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()


# ── Page: Admit Patient ────────────────────────────────────────────────────
if "Admit" in page:
    st.markdown("# 🚨 Admit New Patient")
    st.markdown("Enter patient details. The AI will triage and allocate resources automatically.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("### 👤 Patient Info")
        patient_name = st.text_input("Full Name", placeholder="e.g. Rahul Sharma")
        age = st.number_input("Age", min_value=0, max_value=120, value=40)
        symptoms = st.text_area(
            "Symptoms",
            placeholder="Describe symptoms in detail...\ne.g. Severe chest pain radiating to left arm, sweating, shortness of breath",
            height=120
        )

    with col2:
        st.markdown("### 💉 Vital Signs")
        v1, v2 = st.columns(2)
        with v1:
            heart_rate = st.number_input("Heart Rate (bpm)", 0, 300, 80)
            systolic_bp = st.number_input("Systolic BP (mmHg)", 0, 300, 120)
            spo2 = st.number_input("SpO₂ (%)", 0, 100, 98)
        with v2:
            diastolic_bp = st.number_input("Diastolic BP (mmHg)", 0, 200, 80)
            temperature = st.number_input("Temperature (°F)", 90.0, 110.0, 98.6, step=0.1)
            resp_rate = st.number_input("Resp Rate (/min)", 0, 60, 16)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Preset scenarios
    st.markdown("**⚡ Quick Presets:**")
    p1, p2, p3, p4 = st.columns(4)
    preset = None
    with p1:
        if st.button("🔴 Cardiac Arrest", use_container_width=True):
            preset = "cardiac"
    with p2:
        if st.button("🟠 Stroke", use_container_width=True):
            preset = "stroke"
    with p3:
        if st.button("🟡 Broken Arm", use_container_width=True):
            preset = "fracture"
    with p4:
        if st.button("🟢 Flu", use_container_width=True):
            preset = "flu"

    presets = {
        "cardiac": {
            "patient_name": "Emergency Patient",
            "age": 58,
            "symptoms": "Cardiac arrest — unresponsive, no pulse",
            "vitals": {"heart_rate": 0, "systolic_bp": 60, "diastolic_bp": 30, "temperature": 96.0, "spo2": 72, "respiratory_rate": 0}
        },
        "stroke": {
            "patient_name": "Emergency Patient",
            "age": 65,
            "symptoms": "Sudden facial drooping, arm weakness, slurred speech — suspected stroke",
            "vitals": {"heart_rate": 105, "systolic_bp": 195, "diastolic_bp": 120, "temperature": 98.2, "spo2": 93, "respiratory_rate": 22}
        },
        "fracture": {
            "patient_name": "Patient",
            "age": 28,
            "symptoms": "Fell from bicycle, right arm pain, possible fracture, no head injury",
            "vitals": {"heart_rate": 90, "systolic_bp": 125, "diastolic_bp": 82, "temperature": 98.6, "spo2": 99, "respiratory_rate": 18}
        },
        "flu": {
            "patient_name": "Patient",
            "age": 32,
            "symptoms": "Flu symptoms — mild fever, body aches, runny nose, cough for 2 days",
            "vitals": {"heart_rate": 85, "systolic_bp": 118, "diastolic_bp": 76, "temperature": 100.4, "spo2": 98, "respiratory_rate": 17}
        }
    }

    if preset:
        p = presets[preset]
        st.session_state["preset_data"] = p
        st.info(f"Preset loaded: **{p['symptoms'][:60]}...**  — Click Submit to process.")

    st.markdown("")
    submit = st.button("🧠 Run AI Triage & Allocate", type="primary", use_container_width=True)

    if submit:
        # Use preset if loaded, else form data
        if "preset_data" in st.session_state and preset:
            payload = st.session_state.pop("preset_data")
        else:
            if not patient_name or not symptoms:
                st.error("Please enter patient name and symptoms.")
                st.stop()
            payload = {
                "patient_name": patient_name,
                "age": int(age),
                "symptoms": symptoms,
                "vitals": {
                    "heart_rate": int(heart_rate),
                    "systolic_bp": int(systolic_bp),
                    "diastolic_bp": int(diastolic_bp),
                    "temperature": float(temperature),
                    "spo2": int(spo2),
                    "respiratory_rate": int(resp_rate)
                }
            }

        with st.spinner("🤖 AI is analyzing patient data..."):
            result, code = admit_patient(payload)

        if code == 200 and "error" not in result:
            level = result.get("priority_level", "Unknown")
            score = result.get("priority_score", 0)
            status = result.get("status", "")

            # Header banner by priority
            colors = {"Critical": "#ff1744", "High": "#ff6d00", "Medium": "#ffd600", "Low": "#00e676"}
            color = colors.get(level, "#00d4ff")

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {color}22, {color}11);
                        border: 2px solid {color}; border-radius: 16px; padding: 24px; margin: 16px 0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h2 style="margin:0; color:{color};">
                            {"🚨" if level=="Critical" else "⚠️" if level=="High" else "🟡" if level=="Medium" else "✅"}
                            {level} Priority
                        </h2>
                        <p style="color:#aaa; margin:4px 0 0 0;">Patient ID: <b style="color:#fff; font-family:monospace;">{result.get("patient_id")}</b></p>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:48px; font-weight:700; color:{color}; font-family:monospace;">{score}</div>
                        <div style="color:#aaa; font-size:12px;">TRIAGE SCORE</div>
                    </div>
                </div>
            </div>,
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""<div class="result-card">
                    <div style="color:#7a9bb5;font-size:11px;letter-spacing:1px;">ASSIGNED BED</div>
                    <div style="font-size:24px;font-weight:700;color:#00d4ff;margin-top:6px;">{result.get("assigned_bed") or "Waiting"}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="result-card">
                    <div style="color:#7a9bb5;font-size:11px;letter-spacing:1px;">ASSIGNED DOCTOR</div>
                    <div style="font-size:18px;font-weight:700;color:#00d4ff;margin-top:6px;">{result.get("assigned_doctor") or "Pending"}</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                wait = result.get("estimated_wait_minutes", 0)
                wait_color = "#ff1744" if wait == 0 else "#ffd600" if wait < 20 else "#aaa"
                st.markdown(f"""<div class="result-card">
                    <div style="color:#7a9bb5;font-size:11px;letter-spacing:1px;">EST. WAIT TIME</div>
                    <div style="font-size:24px;font-weight:700;color:{wait_color};margin-top:6px;">{wait} min</div>
                </div>""", unsafe_allow_html=True)

            st.markdown(f"""
            <div class="result-card">
                <div style="color:#7a9bb5;font-size:11px;letter-spacing:1px;margin-bottom:8px;">🤖 AI CLINICAL REASONING</div>
                <div style="color:#e0f0ff;">{result.get("priority_reasoning", "—")}</div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.error(f"❌ Error: {result.get('error', result.get('detail', 'Unknown error'))}")


# ── Page: Patient Queue ────────────────────────────────────────────────────
elif "Queue" in page:
    st.markdown("# 📋 Patient Queue")

    patients = get_patients()

    if not patients:
        st.info("No patients admitted yet.")
    else:
        priority_filter = st.multiselect(
            "Filter by Priority",
            ["Critical", "High", "Medium", "Low"],
            default=["Critical", "High", "Medium", "Low"]
        )

        filtered = [
    p for p in patients
    if p.get("priority_level") in priority_filter
    and str(p.get("status", "")).strip().lower() != "discharged"
]

        st.markdown(f"**{len(filtered)} patient(s)** | sorted by most recent")
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        for p in filtered:
            level = p.get("priority_level", "Low")
            colors = {"Critical": "#ff1744", "High": "#ff6d00", "Medium": "#ffd600", "Low": "#00e676"}
            color = colors.get(level, "#aaa")

            with st.expander(
                f"{'🔴' if level=='Critical' else '🟠' if level=='High' else '🟡' if level=='Medium' else '🟢'} "
                f"**{p.get('patient_name') or 'Unknown'}** — {p.get('status')} — ID: {p.get('patient_id')}"
            ):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"**Age:** {p.get('age')}")
                    st.markdown(f"**Priority:** {level} (Score: {p.get('priority_score')})")
                    st.markdown(f"**Bed:** {p.get('assigned_bed') or 'Not assigned'}")
                with c2:
                    st.markdown(f"**Doctor:** {p.get('assigned_doctor') or 'Pending'}")
                    st.markdown(f"**Wait:** {p.get('estimated_wait_minutes')} min")
                    st.markdown(f"**Time:** {p.get('timestamp', '')[:19]}")
                with c3:
                    st.markdown(f"**Symptoms:**")
                    st.caption(p.get("symptoms", "—"))

                st.markdown(f"**🤖 AI Reasoning:** {p.get('priority_reasoning', '—')}")

                if str(p.get("status", "")).strip().lower() != "discharged":

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            f"✅ Discharge",
                            key=f"d_{p['patient_id']}"
                        ):
                            if discharge(p["patient_id"]):
                                st.success("Patient discharged successfully.")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Failed to discharge patient.")


                    with col2:
                        if not p.get("assigned_doctor"):
                            if st.button(
                                f"👨‍⚕️ Assign Doctor",
                                key=f"a_{p['patient_id']}"
                            ):
                                result, code = assign_doctor(p["patient_id"])

                                if code == 200:
                                    st.success(f"Doctor assigned: {result.get('assigned_doctor')}")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(result.get("detail", "No doctor available"))
                        else:
                            st.success(f"👨‍⚕️ Doctor Assigned")


# ── Page: Dashboard ────────────────────────────────────────────────────────
elif "Dashboard" in page:
    st.markdown("# 📊 System Dashboard")

    res = get_resources()
    patients = get_patients()

    # Resource metrics
    st.markdown("### 🏥 Resource Status")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class="metric-box">
            <div class="metric-number">{res.get("icu_beds","—")}</div>
            <div class="metric-label">ICU Beds Free</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="metric-box">
            <div class="metric-number">{res.get("general_beds","—")}</div>
            <div class="metric-label">Gen Beds Free</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="metric-box">
            <div class="metric-number">{res.get("doctors","—")}</div>
            <div class="metric-label">Doctors Available</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        active = len([p for p in patients if p.get("status") != "Discharged"])
        st.markdown(f"""<div class="metric-box">
            <div class="metric-number">{active}</div>
            <div class="metric-label">Active Patients</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Priority breakdown
    if patients:
        st.markdown("### 📈 Patient Statistics")
        from collections import Counter
        priority_counts = Counter(p.get("priority_level", "Unknown") for p in patients)

        cols = st.columns(4)
        for i, (lvl, clr) in enumerate([
            ("Critical", "#ff1744"), ("High", "#ff6d00"),
            ("Medium", "#ffd600"), ("Low", "#00e676")
        ]):
            with cols[i]:
                count = priority_counts.get(lvl, 0)
                st.markdown(f"""<div class="metric-box" style="border-color:{clr}33;">
                    <div class="metric-number" style="color:{clr};">{count}</div>
                    <div class="metric-label">{lvl}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # Recent admissions table
        st.markdown("### 🕐 Recent Admissions")
        import pandas as pd
        df = pd.DataFrame(patients[:20])[[
            "patient_id", "patient_name", "age", "priority_level",
            "priority_score", "assigned_bed", "assigned_doctor",
            "status", "timestamp"
        ]]
        df.columns = ["ID", "Name", "Age", "Priority", "Score", "Bed", "Doctor", "Status", "Time"]
        df["Time"] = df["Time"].str[:19]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No patient data yet. Start admitting patients.")
