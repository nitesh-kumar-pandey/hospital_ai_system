"""
🏥 AI Hospital Resource Allocation — Streamlit Frontend
Run: streamlit run frontend/streamlit_app.py
"""

import streamlit as st
import requests
import time
from collections import Counter
from datetime import datetime

import pandas as pd

# ── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Hospital Allocation",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000/api/v1"

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0f1e 0%, #0d1b2a 100%);
    border-right: 1px solid rgba(0,212,255,0.15);
}
[data-testid="stSidebar"] * { color: #e0f0ff !important; }

.stApp { background: #060d18; }

/* Priority badges */
.badge-critical { background:#ff1744; color:white;  padding:4px 12px; border-radius:20px; font-weight:600; font-size:12px; letter-spacing:1px; }
.badge-high     { background:#ff6d00; color:white;  padding:4px 12px; border-radius:20px; font-weight:600; font-size:12px; letter-spacing:1px; }
.badge-medium   { background:#ffd600; color:#000;   padding:4px 12px; border-radius:20px; font-weight:600; font-size:12px; letter-spacing:1px; }
.badge-low      { background:#00e676; color:#000;   padding:4px 12px; border-radius:20px; font-weight:600; font-size:12px; letter-spacing:1px; }

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
.metric-number { font-size:36px; font-weight:700; color:#00d4ff; font-family:'JetBrains Mono',monospace; }
.metric-label  { font-size:12px; color:#7a9bb5; letter-spacing:1px; text-transform:uppercase; margin-top:4px; }

h1, h2, h3 { color: #e0f0ff !important; }

.status-assigned { color:#00e676; font-weight:600; }
.status-waiting  { color:#ffd600; font-weight:600; }
.status-error    { color:#ff1744; font-weight:600; }

.section-divider {
    border: none;
    border-top: 1px solid rgba(0,212,255,0.1);
    margin: 24px 0;
}

/* XAI factor cards */
.factor-high   { border-left:4px solid #ff1744; background:#1a0a0a; padding:12px 16px; border-radius:8px; margin:6px 0; }
.factor-medium { border-left:4px solid #ffd600; background:#1a1600; padding:12px 16px; border-radius:8px; margin:6px 0; }
.factor-low    { border-left:4px solid #00e676; background:#001a09; padding:12px 16px; border-radius:8px; margin:6px 0; }

/* Report urgency */
.urgency-critical { background:#ff174422; border:1px solid #ff1744; border-radius:10px; padding:12px 16px; margin:8px 0; }
.urgency-watch    { background:#ffd60022; border:1px solid #ffd600; border-radius:10px; padding:12px 16px; margin:8px 0; }
.urgency-normal   { background:#00e67622; border:1px solid #00e676; border-radius:10px; padding:12px 16px; margin:8px 0; }
</style>
""", unsafe_allow_html=True)


# ── API helpers ────────────────────────────────────────────────────────────
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


def call_explain(payload: dict):
    try:
        r = requests.post(f"{API_BASE}/explain", json=payload, timeout=20)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def call_smart_doctor(payload: dict):
    try:
        r = requests.post(f"{API_BASE}/smart-doctor", json=payload, timeout=20)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def call_summarise_report(file_bytes: bytes, filename: str, content_type: str):
    try:
        r = requests.post(
            f"{API_BASE}/report/summarise",
            files={"file": (filename, file_bytes, content_type)},
            timeout=60,
        )
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500


# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 MediAI")
    st.markdown("**Resource Allocation System**")
    st.markdown("""
    <div style="background:#0d2a1a;border:1px solid #00e676;border-radius:8px;
                padding:8px 12px;margin:8px 0;font-size:12px;color:#00e676;">
        ⚡ Powered by <b>Groq</b> — Free LLM API
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigation",
        [
            "🚨 Admit Patient",
            "📄 Medical Report",
            "🧠 Explain AI",
            "📋 Patient Queue",
            "📊 Dashboard",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")

    st.markdown("### 🤖 AI Model")
    groq_model = st.selectbox(
        "Groq Model",
        ["llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"],
        label_visibility="collapsed",
    )
    st.caption(f"Model: `{groq_model}` (free)")
    st.markdown("---")

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


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Admit Patient
# ══════════════════════════════════════════════════════════════════════════
if "Admit" in page:
    st.markdown("# 🚨 Admit New Patient")
    st.markdown("Enter patient details. The AI will triage, explain its decision, and assign the best doctor automatically.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("### 👤 Patient Info")
        patient_name = st.text_input("Full Name", placeholder="e.g. Rahul Sharma")
        age          = st.number_input("Age", min_value=0, max_value=120, value=40)
        symptoms     = st.text_area(
            "Symptoms",
            placeholder="Describe symptoms in detail...\ne.g. Severe chest pain radiating to left arm, sweating, shortness of breath",
            height=120,
        )

    with col2:
        st.markdown("### 💓 Vitals")
        v1, v2 = st.columns(2)
        with v1:
            heart_rate = st.number_input("Heart Rate (bpm)",   0, 300,   80)
            systolic   = st.number_input("Systolic BP (mmHg)", 0, 300,  120)
            diastolic  = st.number_input("Diastolic BP (mmHg)",0, 200,   80)
        with v2:
            spo2       = st.number_input("SpO2 (%)",           0, 100,   98)
            temp       = st.number_input("Temperature (°F)",  90.0, 110.0, 98.6, step=0.1)
            resp_rate  = st.number_input("Respiratory Rate (/min)", 0, 60, 16)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if st.button("🚀 Admit & Triage Patient", use_container_width=True, type="primary"):
        if not patient_name or not symptoms:
            st.error("Please fill in patient name and symptoms.")
        else:
            vitals_payload = {
                "heart_rate":       heart_rate,
                "systolic_bp":      systolic,
                "diastolic_bp":     diastolic,
                "spo2":             spo2,
                "temperature":      temp,
                "respiratory_rate": resp_rate,
            }
            admit_payload = {
                "patient_name": patient_name,
                "age":          age,
                "symptoms":     symptoms,
                "vitals":       vitals_payload,
            }

            # ── Step 1: Admit & triage ────────────────────────────────────
            with st.spinner("🤖 Admitting patient and calculating triage score..."):
                result, code = admit_patient(admit_payload)

            if code != 200:
                st.error(f"❌ Admission failed: {result.get('error', result.get('detail', 'Unknown error'))}")
                st.stop()

            level     = result.get("priority_level", "Low")
            score     = result.get("priority_score", 0)
            color_map = {
                "Critical": "#ff1744",
                "High":     "#ff6d00",
                "Medium":   "#ffd600",
                "Low":      "#00e676",
            }
            color = color_map.get(level, "#aaa")

            # ── Triage banner ─────────────────────────────────────────────
            emoji = "🚨" if level == "Critical" else "⚠️" if level == "High" else "🟡" if level == "Medium" else "✅"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,{color}22,{color}11);
                        border:2px solid {color};border-radius:16px;
                        padding:24px;margin:16px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <h2 style="margin:0;color:{color};">{emoji} {level} Priority</h2>
                        <p style="color:#aaa;margin:4px 0 0;">
                            Patient ID: <b style="color:#fff;font-family:monospace;">{result.get("patient_id")}</b>
                        </p>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:48px;font-weight:700;color:{color};font-family:monospace;">{score}</div>
                        <div style="color:#aaa;font-size:12px;">TRIAGE SCORE</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Resource summary cards ────────────────────────────────────
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="result-card">
                    <div style="color:#7a9bb5;font-size:11px;letter-spacing:1px;">ASSIGNED BED</div>
                    <div style="font-size:24px;font-weight:700;color:#00d4ff;margin-top:6px;">
                        {result.get("assigned_bed") or "Waiting"}
                    </div>
                </div>""", unsafe_allow_html=True)
            with c2:
                # Doctor will be filled in after smart allocation below; use placeholder for now
                st.markdown(f"""
                <div class="result-card">
                    <div style="color:#7a9bb5;font-size:11px;letter-spacing:1px;">ASSIGNED DOCTOR</div>
                    <div id="doctor-slot" style="font-size:18px;font-weight:700;color:#00d4ff;margin-top:6px;">
                        {result.get("assigned_doctor") or "Allocating…"}
                    </div>
                </div>""", unsafe_allow_html=True)
            with c3:
                wait       = result.get("estimated_wait_minutes", 0)
                wait_color = "#ff1744" if wait == 0 else "#ffd600" if wait < 20 else "#aaa"
                st.markdown(f"""
                <div class="result-card">
                    <div style="color:#7a9bb5;font-size:11px;letter-spacing:1px;">EST. WAIT TIME</div>
                    <div style="font-size:24px;font-weight:700;color:{wait_color};margin-top:6px;">{wait} min</div>
                </div>""", unsafe_allow_html=True)

            # ── AI clinical reasoning ─────────────────────────────────────
            st.markdown(f"""
            <div class="result-card">
                <div style="color:#7a9bb5;font-size:11px;letter-spacing:1px;margin-bottom:8px;">
                    🤖 AI CLINICAL REASONING
                </div>
                <div style="color:#e0f0ff;">{result.get("priority_reasoning", "—")}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

            # ── Step 2: XAI explanation ───────────────────────────────────
            st.markdown("### 🧠 Why This Priority? — AI Explanation")
            with st.spinner("🔍 Analysing risk factors..."):
                xai_payload = {
                    "symptoms":       symptoms,
                    "vitals":         vitals_payload,
                    "age":            age,
                    "priority_level": level,
                    "priority_score": score,
                }
                xai_result, xai_code = call_explain(xai_payload)

            predicted_condition = None

            if xai_code == 200 and not xai_result.get("error"):
                predicted_condition = xai_result.get("predicted_condition")
                confidence          = xai_result.get("confidence", "Medium")
                conf_color          = (
                    "#00e676" if confidence == "High"
                    else "#ffd600" if confidence == "Medium"
                    else "#ff6d00"
                )

                # Predicted condition + confidence banner
                st.markdown(f"""
                <div class="result-card" style="margin-bottom:12px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div style="color:#7a9bb5;font-size:11px;letter-spacing:1px;">PREDICTED CONDITION</div>
                            <div style="font-size:20px;font-weight:700;color:#e0f0ff;margin-top:4px;">
                                🩺 {predicted_condition or "—"}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:11px;color:#7a9bb5;letter-spacing:1px;">AI CONFIDENCE</div>
                            <div style="font-size:22px;font-weight:700;color:{conf_color};">{confidence}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Plain language summary
                plain = xai_result.get("plain_summary", "")
                if plain:
                    st.info(f"📋 {plain}")

                # Clinical note
                clinical = xai_result.get("clinical_note", "")
                if clinical:
                    st.markdown(f"""
                    <div style="background:#0d1b2a;border:1px solid #00d4ff33;border-radius:8px;
                                padding:12px 16px;margin:6px 0 12px;">
                        <b style="color:#00d4ff;font-size:11px;">🏥 CLINICAL NOTE</b><br>
                        <span style="color:#b0c8d8;">{clinical}</span>
                    </div>
                    """, unsafe_allow_html=True)

                # Top contributing risk factors
                top_factors = xai_result.get("top_factors", [])
                if top_factors:
                    st.markdown("**📊 Top Contributing Risk Factors:**")
                    for f in top_factors:
                        impact     = f.get("impact", "low")
                        direction  = f.get("direction", "neutral")
                        icon       = "🔴" if impact == "high" else "🟡" if impact == "medium" else "🟢"
                        arrow      = "↑" if direction == "increases_risk" else "↓" if direction == "decreases_risk" else "→"
                        factor_css = f"factor-{impact}"
                        st.markdown(f"""
                        <div class="{factor_css}">
                            <div style="display:flex;justify-content:space-between;">
                                <b style="color:#e0f0ff;">{icon} {f.get("factor", "")}</b>
                                <span style="color:#7a9bb5;font-size:12px;font-family:monospace;">
                                    {arrow} {impact.upper()} &nbsp;|&nbsp; {f.get("value", "")}
                                </span>
                            </div>
                            <div style="color:#b0c8d8;font-size:13px;margin-top:4px;">
                                {f.get("plain_explanation", "")}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ AI explanation could not be generated for this patient.")

            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

            # ── Step 3: Doctor card + email status ────────────────────────
            # The backend /allocate endpoint already ran smart doctor
            # allocation AND sent the email. We just display what came back.
            doc_name     = result.get("assigned_doctor")
            spec         = result.get("doctor_spec", result.get("specialization", "—"))
            sd_score     = result.get("match_score", 0)
            reason       = result.get("match_reason", result.get("priority_reasoning", "—"))
            email_status = result.get("email_status", {})

            if doc_name:
                sc_color = (
                    "#00e676" if sd_score >= 70
                    else "#ffd600" if sd_score >= 40
                    else "#ff6d00"
                )

                # Doctor card
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#0a1f2a,#0d2a3a);
                            border:2px solid #00d4ff44;border-radius:14px;
                            padding:20px;margin:4px 0 10px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div style="font-size:11px;color:#7a9bb5;
                                        letter-spacing:1px;margin-bottom:4px;">
                                👨‍⚕️ ASSIGNED DOCTOR
                            </div>
                            <div style="font-size:22px;font-weight:700;
                                        color:#00d4ff;">{doc_name}</div>
                            <div style="color:#b0c8d8;margin-top:4px;font-size:13px;">
                                <b>Specialization:</b> {spec or "—"}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:11px;color:#7a9bb5;
                                        letter-spacing:1px;">MATCH SCORE</div>
                            <div style="font-size:36px;font-weight:700;
                                        color:{sc_color};font-family:monospace;">
                                {sd_score}<span style="font-size:14px;
                                color:#7a9bb5;">/100</span>
                            </div>
                        </div>
                    </div>
                    <div style="background:#0a1525;border-radius:8px;
                                padding:10px 12px;margin-top:12px;">
                        <b style="color:#7a9bb5;font-size:11px;">WHY THIS DOCTOR</b><br>
                        <span style="color:#e0f0ff;font-size:13px;">{reason}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Email notification status banner
                if email_status.get("sent"):
                    st.markdown(f"""
                    <div style="background:#00e67611;border:1px solid #00e676;
                                border-radius:10px;padding:12px 16px;margin:6px 0;">
                        <span style="color:#00e676;font-weight:600;">
                            ✉️ Email notification sent
                        </span>
                        <span style="color:#b0c8d8;font-size:13px;margin-left:8px;">
                            — {email_status.get('message', '')}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    em_msg = email_status.get("message", "Email not sent.")
                    # Only show warning if it's a real failure, not dev-mode skip
                    if "disabled" in em_msg.lower() or "dev mode" in em_msg.lower():
                        st.markdown(f"""
                        <div style="background:#ffd60011;border:1px solid #ffd600;
                                    border-radius:10px;padding:10px 14px;margin:6px 0;">
                            <span style="color:#ffd600;font-weight:600;">
                                📧 Email disabled (dev mode)
                            </span>
                            <span style="color:#b0c8d8;font-size:12px;margin-left:6px;">
                                — Set EMAIL_ENABLED=true and configure SMTP_* in .env to enable.
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.warning(
                            f"⚠️ Patient admitted successfully, but doctor email notification "
                            f"failed: {em_msg}"
                        )
            else:
                st.warning("⚠️ All doctors are currently busy — patient added to the queue.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Medical Report Summarisation
# ══════════════════════════════════════════════════════════════════════════
elif "Report" in page:
    st.markdown("# 📄 Medical Report Summarisation")
    st.markdown("Upload a medical report (PDF, image, or text). The AI will extract and summarise key information.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload Medical Report",
        type=["pdf", "png", "jpg", "jpeg", "bmp", "tiff", "txt"],
        help="Supports PDF, scanned images (PNG/JPG), and plain text files up to 10 MB",
    )

    if uploaded:
        st.markdown(f"**File:** `{uploaded.name}` — {uploaded.size // 1024} KB")

        if st.button("🔍 Analyse Report", use_container_width=True, type="primary"):
            file_bytes  = uploaded.read()
            content_map = {
                "pdf":  "application/pdf",
                "png":  "image/png",
                "jpg":  "image/jpeg",
                "jpeg": "image/jpeg",
                "bmp":  "image/bmp",
                "tiff": "image/tiff",
                "txt":  "text/plain",
            }
            ext          = uploaded.name.rsplit(".", 1)[-1].lower()
            content_type = content_map.get(ext, "application/octet-stream")

            with st.spinner("📖 Extracting text and generating summary..."):
                result, code = call_summarise_report(file_bytes, uploaded.name, content_type)

            if code != 200:
                st.error(f"❌ {result.get('detail', result.get('error', 'Unknown error'))}")
                st.stop()

            # Urgency flag
            urgency = result.get("urgency_flag", "Normal")
            urgency_styles = {
                "Critical": ("urgency-critical", "🚨", "#ff1744", "URGENT — Immediate medical attention required"),
                "Watch":    ("urgency-watch",    "⚠️", "#ffd600", "MONITOR — Abnormal values detected"),
                "Normal":   ("urgency-normal",   "✅", "#00e676", "NORMAL — No immediate concerns"),
            }
            cls, icon, clr, label = urgency_styles.get(urgency, urgency_styles["Normal"])
            st.markdown(f"""
            <div class="{cls}">
                <b style="color:{clr};font-size:16px;">{icon} {urgency} — {label}</b>
            </div>
            """, unsafe_allow_html=True)

            # Patient-friendly summary
            st.markdown("### 🗣️ Patient-Friendly Summary")
            st.info(result.get("patient_friendly_summary") or "Summary not available.")

            # Structured details
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 🩺 Diagnosis")
                for d in (result.get("diagnosis") or []):
                    st.markdown(f"- {d}")
                if not result.get("diagnosis"):
                    st.caption("No diagnosis extracted.")

                st.markdown("#### 💊 Medications")
                for m in (result.get("medications") or []):
                    st.markdown(f"- {m}")
                if not result.get("medications"):
                    st.caption("No medications listed.")

                st.markdown("#### 📌 Recommendations")
                for r in (result.get("recommendations") or []):
                    st.markdown(f"- {r}")
                if not result.get("recommendations"):
                    st.caption("No recommendations found.")

            with col2:
                st.markdown("#### 😷 Symptoms Identified")
                for s in (result.get("symptoms") or []):
                    st.markdown(f"- {s}")
                if not result.get("symptoms"):
                    st.caption("No symptoms extracted.")

                st.markdown("#### 🔬 Lab Results")
                labs = result.get("lab_results") or {}
                for test, val in labs.items():
                    st.markdown(f"- **{test}:** {val}")
                if not labs:
                    st.caption("No lab results found.")

                st.markdown("#### 📝 Doctor's Notes")
                st.caption(result.get("doctor_notes") or "—")

            # Raw text toggle
            if result.get("raw_text"):
                with st.expander("📃 View Raw Extracted Text"):
                    st.text(result["raw_text"][:3000])
    else:
        st.markdown("""
        <div class="result-card" style="text-align:center;padding:40px;">
            <div style="font-size:48px;">📄</div>
            <p style="color:#7a9bb5;margin:12px 0 4px;">Upload a medical report to get started</p>
            <p style="color:#3a5a75;font-size:13px;">Supported formats: PDF, PNG, JPG, TIFF, BMP, TXT</p>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Explainable AI (standalone — for any patient data)
# ══════════════════════════════════════════════════════════════════════════
elif "Explain" in page:
    st.markdown("# 🧠 Explainable AI — Decision Breakdown")
    st.markdown("Understand **why** the AI assigned a priority level. Select an admitted patient to see a factor-by-factor breakdown.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    patients   = get_patients()
    active_pts = [p for p in patients if p.get("status") != "Discharged"]
    pt_options = {f"{p['patient_id']} — {p.get('patient_name', '?')}": p for p in active_pts}

    if not pt_options:
        st.info("No active patients found. Admit a patient first to use this page.")
        st.stop()

    selected_key = st.selectbox("Select an admitted patient", list(pt_options.keys()))
    pt           = pt_options[selected_key]
    symptoms     = pt.get("symptoms", "")
    vitals       = pt.get("vitals", {})
    age_val      = pt.get("age", 40)
    priority_lvl = pt.get("priority_level", "Medium")
    priority_sc  = pt.get("priority_score", 50)
    st.info(f"Patient: **{pt.get('patient_name')}** | Age: {age_val} | Priority: **{priority_lvl}**")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if st.button("🔬 Generate Explanation", use_container_width=True, type="primary"):
        if not symptoms:
            st.error("Selected patient has no symptoms recorded.")
        else:
            payload = {
                "symptoms":       symptoms,
                "vitals":         vitals,
                "age":            age_val,
                "priority_level": priority_lvl if priority_lvl != "Unknown" else None,
                "priority_score": priority_sc,
            }
            with st.spinner("🧠 Analysing contributing factors..."):
                xai, code = call_explain(payload)

            if code != 200:
                st.error(f"❌ {xai.get('detail', xai.get('error', 'Error'))}")
                st.stop()

            # Prediction banner
            pred_condition = xai.get("predicted_condition", "Unknown")
            confidence     = xai.get("confidence", "Medium")
            conf_color     = {"High": "#00e676", "Medium": "#ffd600", "Low": "#ff6d00"}.get(confidence, "#aaa")
            st.markdown(f"""
            <div class="result-card">
                <div style="font-size:11px;color:#7a9bb5;letter-spacing:1px;margin-bottom:8px;">🔮 PREDICTED CONDITION</div>
                <div style="font-size:22px;font-weight:700;color:#e0f0ff;">{pred_condition}</div>
                <div style="margin-top:8px;">
                    Confidence: <b style="color:{conf_color};">{confidence}</b>
                    &nbsp;&nbsp;|&nbsp;&nbsp;
                    Priority: <b style="color:#00d4ff;">{xai.get("priority_level", "—")}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Plain summary
            st.markdown("### 🗣️ Plain Language Explanation")
            st.info(xai.get("plain_summary", "—"))

            if xai.get("clinical_note"):
                st.markdown(f"""
                <div style="background:#0a1f1a;border:1px solid #00e67644;border-radius:8px;
                            padding:12px 16px;margin:8px 0;">
                    🩺 <b style="color:#00e676;">Clinical Note:</b>
                    <span style="color:#cce8d0;">{xai["clinical_note"]}</span>
                </div>
                """, unsafe_allow_html=True)

            # Factor breakdown
            st.markdown("### 📊 Contributing Factors")
            st.caption("Ranked by impact on the AI's priority decision")
            for f in xai.get("top_factors", []):
                impact    = f.get("impact", "low")
                direction = f.get("direction", "neutral")
                icon      = "🔴" if impact == "high" else "🟡" if impact == "medium" else "🟢"
                arrow     = "↑" if direction == "increases_risk" else "↓" if direction == "decreases_risk" else "→"
                st.markdown(f"""
                <div class="factor-{impact}">
                    <b style="color:#e0f0ff;">{icon} {f.get("factor")} — {f.get("value")}</b>
                    <span style="color:#7a9bb5;font-size:12px;margin-left:8px;">
                        ({arrow} {impact.upper()} impact)
                    </span>
                    <br>
                    <span style="color:#b0c8d8;font-size:13px;margin-top:4px;display:block;">
                        {f.get("plain_explanation")}
                    </span>
                </div>
                """, unsafe_allow_html=True)

            with st.expander("ℹ️ About this explanation"):
                st.markdown("""
                This explanation uses a **rule-based feature attribution system** that analyses
                each vital sign and symptom individually against clinical thresholds.

                **To integrate SHAP/LIME** (advanced XAI):
                - Train a scikit-learn model on historical triage data
                - Use `shap.TreeExplainer` or `lime.tabular.LimeTabularExplainer`
                - Replace `_analyse_vitals()` in `explain_service.py` with SHAP/LIME values
                - Install: `pip install shap lime`
                """)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Patient Queue
# ══════════════════════════════════════════════════════════════════════════
elif "Queue" in page:
    st.markdown("# 📋 Patient Queue")

    patients = get_patients()

    if not patients:
        st.info("No patients admitted yet.")
    else:
        priority_filter = st.multiselect(
            "Filter by Priority",
            ["Critical", "High", "Medium", "Low"],
            default=["Critical", "High", "Medium", "Low"],
        )
        filtered = [
            p for p in patients
            if p.get("priority_level") in priority_filter
            and str(p.get("status", "")).strip().lower() != "discharged"
        ]
        st.markdown(f"**{len(filtered)} patient(s)** | sorted by most recent")
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        for p in filtered:
            level  = p.get("priority_level", "Low")
            colors = {"Critical": "#ff1744", "High": "#ff6d00", "Medium": "#ffd600", "Low": "#00e676"}
            color  = colors.get(level, "#aaa")

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
                    st.markdown("**Symptoms:**")
                    st.caption(p.get("symptoms", "—"))

                st.markdown(f"**🤖 AI Reasoning:** {p.get('priority_reasoning', '—')}")

                if str(p.get("status", "")).strip().lower() != "discharged":
                    ba1, ba2 = st.columns(2)
                    with ba1:
                        if st.button("✅ Discharge", key=f"d_{p['patient_id']}"):
                            if discharge(p["patient_id"]):
                                st.success("Patient discharged successfully.")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Failed to discharge patient.")
                    with ba2:
                        if not p.get("assigned_doctor"):
                            if st.button("👨‍⚕️ Assign Doctor", key=f"a_{p['patient_id']}"):
                                r, code = assign_doctor(p["patient_id"])
                                if code == 200:
                                    st.success(f"Doctor assigned: {r.get('assigned_doctor')}")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(r.get("detail", "No doctor available"))
                        else:
                            st.success("👨‍⚕️ Doctor Assigned")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ══════════════════════════════════════════════════════════════════════════
elif "Dashboard" in page:
    st.markdown("# 📊 System Dashboard")

    res      = get_resources()
    patients = get_patients()

    st.markdown("### 🏥 Resource Status")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class="metric-box">
            <div class="metric-number">{res.get("icu_beds", "—")}</div>
            <div class="metric-label">ICU Beds Free</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="metric-box">
            <div class="metric-number">{res.get("general_beds", "—")}</div>
            <div class="metric-label">Gen Beds Free</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="metric-box">
            <div class="metric-number">{res.get("doctors", "—")}</div>
            <div class="metric-label">Doctors Available</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        active = len([p for p in patients if p.get("status") != "Discharged"])
        st.markdown(f"""<div class="metric-box">
            <div class="metric-number">{active}</div>
            <div class="metric-label">Active Patients</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if patients:
        st.markdown("### 📈 Patient Statistics")
        pc = Counter(p.get("priority_level", "Unknown") for p in patients)

        cols = st.columns(4)
        for i, (lvl, clr) in enumerate([
            ("Critical", "#ff1744"),
            ("High",     "#ff6d00"),
            ("Medium",   "#ffd600"),
            ("Low",      "#00e676"),
        ]):
            with cols[i]:
                st.markdown(f"""<div class="metric-box" style="border-color:{clr}33;">
                    <div class="metric-number" style="color:{clr};">{pc.get(lvl, 0)}</div>
                    <div class="metric-label">{lvl}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("### 🕐 Recent Admissions")
        df = pd.DataFrame(patients[:20])[[
            "patient_id", "patient_name", "age", "priority_level",
            "priority_score", "assigned_bed", "assigned_doctor",
            "status", "timestamp",
        ]]
        df.columns = ["ID", "Name", "Age", "Priority", "Score", "Bed", "Doctor", "Status", "Time"]
        df["Time"] = df["Time"].str[:19]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No patient data yet. Start admitting patients.")