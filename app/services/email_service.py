"""
Doctor Email Notification Service
Sends HTML + plain-text email to assigned doctor using SMTP.
"""

import os
import smtplib
import textwrap
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.utils.logger import get_logger

logger = get_logger(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "MediAI Hospital")
EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "true").strip().lower() != "false"

_PRIORITY_COLOR = {
    "Critical": "#ff1744",
    "High": "#ff6d00",
    "Medium": "#ffd600",
    "Low": "#00c853",
}

_PRIORITY_EMOJI = {
    "Critical": "🚨",
    "High": "⚠️",
    "Medium": "🟡",
    "Low": "✅",
}


def _build_plain(doctor_name: str, patient: dict, triage: dict) -> str:
    priority = triage.get("priority_level", "Unknown")
    score = triage.get("priority_score", "—")
    condition = triage.get("predicted_condition", "Under evaluation")
    reason = triage.get("match_reason") or triage.get("priority_reasoning", "—")
    spec = triage.get("specialization", "—")
    ts = datetime.now().strftime("%d %b %Y, %I:%M %p")

    vitals_lines = ""
    for k, v in (patient.get("vitals") or {}).items():
        vitals_lines += f"  • {k.replace('_', ' ').title()}: {v}\n"

    return textwrap.dedent(f"""
    Dear {doctor_name},

    A new patient has been assigned to you based on your expertise in {spec}.

    PATIENT INFORMATION
    Name       : {patient.get('patient_name', '—')}
    Age        : {patient.get('age', '—')} years
    Patient ID : {patient.get('patient_id', '—')}
    Time       : {ts}

    SYMPTOMS
    {patient.get('symptoms', '—')}

    VITALS
    {vitals_lines.strip() or 'Not recorded'}

    TRIAGE RESULT
    Priority Level      : {priority}
    Triage Score        : {score}/100
    Suspected Condition : {condition}
    Specialty           : {spec}

    AI REFERRAL REASON
    {reason}

    IMPORTANT
    This email was generated automatically by MediAI Hospital System.
    Please verify all information clinically.

    Regards,
    MediAI Hospital System
    """).strip()


def _build_html(doctor_name: str, patient: dict, triage: dict) -> str:
    priority = triage.get("priority_level", "Unknown")
    score = triage.get("priority_score", "—")
    condition = triage.get("predicted_condition", "Under evaluation")
    reason = triage.get("match_reason") or triage.get("priority_reasoning", "—")
    spec = triage.get("specialization", "—")
    color = _PRIORITY_COLOR.get(priority, "#888888")
    emoji = _PRIORITY_EMOJI.get(priority, "•")
    ts = datetime.now().strftime("%d %b %Y, %I:%M %p")

    vitals_rows = ""
    for k, v in (patient.get("vitals") or {}).items():
        label = k.replace("_", " ").title()
        vitals_rows += f"""
        <tr>
            <td style="padding:8px 12px;color:#7a9bb5;border-bottom:1px solid #1a2a3a;">{label}</td>
            <td style="padding:8px 12px;color:#e0f0ff;border-bottom:1px solid #1a2a3a;font-weight:600;">{v}</td>
        </tr>
        """

    if not vitals_rows:
        vitals_rows = """
        <tr>
            <td colspan="2" style="padding:8px 12px;color:#7a9bb5;">Not recorded</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#060d18;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#060d18;padding:30px;">
<tr>
<td align="center">

<table width="620" cellpadding="0" cellspacing="0"
style="background:#0d1b2a;border-radius:16px;border:1px solid rgba(0,212,255,0.2);overflow:hidden;">

<tr>
<td style="padding:28px;background:#0a0f1e;border-bottom:2px solid {color};">
    <h2 style="margin:0;color:#e0f0ff;">🏥 New Patient Assigned</h2>
    <p style="margin:6px 0 0;color:#7a9bb5;">MediAI Hospital Resource Allocation System</p>
</td>
<td style="padding:28px;background:#0a0f1e;border-bottom:2px solid {color};text-align:right;">
    <div style="display:inline-block;border:2px solid {color};border-radius:12px;padding:10px 16px;">
        <div style="color:{color};font-size:14px;font-weight:bold;">{emoji} {priority}</div>
        <div style="color:{color};font-size:28px;font-weight:bold;">{score}/100</div>
    </div>
</td>
</tr>

<tr>
<td colspan="2" style="padding:26px 32px;">
    <p style="color:#b0c8d8;font-size:15px;">
        Dear <b style="color:#00d4ff;">{doctor_name}</b>,
    </p>
    <p style="color:#b0c8d8;font-size:15px;line-height:1.6;">
        A new patient has been assigned to you based on your expertise in
        <b style="color:#e0f0ff;">{spec}</b>.
    </p>

    <h3 style="color:#00d4ff;margin-top:24px;">Patient Information</h3>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a1525;border-radius:10px;overflow:hidden;">
        <tr>
            <td style="padding:8px 12px;color:#7a9bb5;border-bottom:1px solid #1a2a3a;">Name</td>
            <td style="padding:8px 12px;color:#e0f0ff;border-bottom:1px solid #1a2a3a;font-weight:600;">{patient.get('patient_name', '—')}</td>
        </tr>
        <tr>
            <td style="padding:8px 12px;color:#7a9bb5;border-bottom:1px solid #1a2a3a;">Age</td>
            <td style="padding:8px 12px;color:#e0f0ff;border-bottom:1px solid #1a2a3a;">{patient.get('age', '—')} years</td>
        </tr>
        <tr>
            <td style="padding:8px 12px;color:#7a9bb5;border-bottom:1px solid #1a2a3a;">Patient ID</td>
            <td style="padding:8px 12px;color:#e0f0ff;border-bottom:1px solid #1a2a3a;font-family:monospace;">{patient.get('patient_id', '—')}</td>
        </tr>
        <tr>
            <td style="padding:8px 12px;color:#7a9bb5;">Admitted At</td>
            <td style="padding:8px 12px;color:#e0f0ff;">{ts}</td>
        </tr>
    </table>

    <h3 style="color:#00d4ff;margin-top:24px;">Symptoms</h3>
    <div style="background:#0a1525;border-radius:10px;padding:14px;color:#e0f0ff;line-height:1.6;">
        {patient.get('symptoms', '—')}
    </div>

    <h3 style="color:#00d4ff;margin-top:24px;">Vitals</h3>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a1525;border-radius:10px;overflow:hidden;">
        {vitals_rows}
    </table>

    <h3 style="color:#00d4ff;margin-top:24px;">Triage Result</h3>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a1525;border-radius:10px;overflow:hidden;">
        <tr>
            <td style="padding:8px 12px;color:#7a9bb5;border-bottom:1px solid #1a2a3a;">Priority</td>
            <td style="padding:8px 12px;color:{color};border-bottom:1px solid #1a2a3a;font-weight:bold;">{emoji} {priority} ({score}/100)</td>
        </tr>
        <tr>
            <td style="padding:8px 12px;color:#7a9bb5;border-bottom:1px solid #1a2a3a;">Suspected Condition</td>
            <td style="padding:8px 12px;color:#e0f0ff;border-bottom:1px solid #1a2a3a;">{condition}</td>
        </tr>
        <tr>
            <td style="padding:8px 12px;color:#7a9bb5;">Specialty</td>
            <td style="padding:8px 12px;color:#00d4ff;">{spec}</td>
        </tr>
    </table>

    <h3 style="color:#00d4ff;margin-top:24px;">AI Referral Reason</h3>
    <div style="background:#0a1f1a;border-left:4px solid #00d4ff;border-radius:8px;padding:14px;color:#b0c8d8;line-height:1.6;">
        {reason}
    </div>

    <div style="margin-top:24px;background:#1a0a0a;border:1px solid #ff174433;border-radius:8px;padding:14px;color:#b0c8d8;font-size:13px;">
        ⚠️ This notification was generated automatically. Please verify all information clinically.
    </div>
</td>
</tr>

<tr>
<td colspan="2" style="background:#060d18;padding:18px;text-align:center;color:#3a5a75;font-size:12px;">
    MediAI Hospital System • Generated {ts}
</td>
</tr>

</table>

</td>
</tr>
</table>
</body>
</html>
"""


def send_doctor_notification_email(
    doctor_email: str,
    doctor_name: str,
    patient_data: dict,
    triage_result: dict,
) -> dict:
    if not EMAIL_ENABLED:
        logger.info("Email notifications disabled.")
        return {"success": True, "message": "Email disabled — skipped."}

    if not SMTP_USER or not SMTP_PASSWORD:
        msg = "SMTP credentials missing. Set SMTP_USER and SMTP_PASSWORD in .env."
        logger.warning(msg)
        return {"success": False, "message": msg}

    if not doctor_email:
        msg = f"No email address found for {doctor_name}."
        logger.warning(msg)
        return {"success": False, "message": msg}

    priority = triage_result.get("priority_level", "Unknown")
    patient_name = patient_data.get("patient_name", "Unknown Patient")
    subject = f"New Patient Assigned: {patient_name} — {priority} Priority"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    msg["To"] = doctor_email

    plain_body = _build_plain(doctor_name, patient_data, triage_result)
    html_body = _build_html(doctor_name, patient_data, triage_result)

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {doctor_email} for patient {patient_name}")

        return {
            "success": True,
            "message": f"Email notification sent to {doctor_name} ({doctor_email}).",
        }

    except smtplib.SMTPAuthenticationError:
        msg_err = (
            "SMTP authentication failed. Check SMTP_USER / SMTP_PASSWORD. "
            "For Gmail, use a 16-character App Password."
        )
        logger.error(msg_err)
        return {"success": False, "message": msg_err}

    except smtplib.SMTPException as exc:
        msg_err = f"SMTP error while sending email: {exc}"
        logger.error(msg_err)
        return {"success": False, "message": msg_err}

    except Exception as exc:
        msg_err = f"Unexpected email error: {exc}"
        logger.error(msg_err)
        return {"success": False, "message": msg_err}