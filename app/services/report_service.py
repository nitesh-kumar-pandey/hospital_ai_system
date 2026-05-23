"""
Medical Report Summarisation Service
Supports: PDF, PNG/JPG images, plain text
Uses: PyMuPDF (fitz) for PDF, pytesseract for image OCR, Groq for LLM summarisation
"""

import os
import json
import re
import base64
from pathlib import Path
from app.utils.logger import get_logger
from groq import Groq

logger = get_logger(__name__)
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama3-8b-8192")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ── Text Extraction ─────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = [page.get_text() for page in doc]
        doc.close()
        text = "\n".join(pages).strip()
        logger.info(f"PDF extracted: {len(text)} chars across {len(pages)} page(s)")
        return text
    except ImportError:
        raise RuntimeError(
            "PyMuPDF not installed. Run: pip install pymupdf --break-system-packages"
        )
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}")


def extract_text_from_image(file_bytes: bytes) -> str:
    """OCR an image (PNG/JPG) using pytesseract."""
    try:
        import pytesseract
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        logger.info(f"OCR extracted: {len(text)} chars")
        return text.strip()
    except ImportError:
        raise RuntimeError(
            "pytesseract or Pillow not installed.\n"
            "Run: pip install pytesseract Pillow --break-system-packages\n"
            "Also install Tesseract binary: https://github.com/tesseract-ocr/tesseract"
        )
    except Exception as e:
        raise RuntimeError(f"Image OCR failed: {e}")


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route extraction by file type."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        return extract_text_from_image(file_bytes)
    elif ext in (".txt", ".md"):
        return file_bytes.decode("utf-8", errors="ignore").strip()
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: pdf, png, jpg, txt")


# ── LLM Summarisation ──────────────────────────────────────────────────────

SUMMARY_PROMPT = """You are a medical AI assistant. A medical report has been uploaded.
Your job is to extract key information and produce a patient-friendly summary.

REPORT TEXT:
\"\"\"
{report_text}
\"\"\"

Respond ONLY with a valid JSON object — no markdown, no extra text:
{{
  "patient_name": "<string or null>",
  "age": "<string or null>",
  "diagnosis": ["<diagnosis 1>", "..."],
  "symptoms": ["<symptom 1>", "..."],
  "medications": ["<drug name + dosage>", "..."],
  "lab_results": {{"<test name>": "<value + unit>"}},
  "doctor_notes": "<string or null>",
  "recommendations": ["<recommendation>", "..."],
  "patient_friendly_summary": "<2-3 sentences in simple English a patient can understand>",
  "urgency_flag": "Critical|Watch|Normal"
}}

Rules:
- urgency_flag = Critical if life-threatening values found (e.g. very low/high BP, SpO2 <88%, troponin elevated)
- urgency_flag = Watch if abnormal values need monitoring
- urgency_flag = Normal otherwise
- Use empty lists/null if information is not present — do NOT invent data
- patient_friendly_summary must avoid medical jargon
"""


def summarise_report(raw_text: str) -> dict:
    """Send extracted report text to Groq and return structured summary dict."""
    if not raw_text or len(raw_text.strip()) < 20:
        return {"error": "Report text is too short or empty to summarise."}

    # Truncate to avoid token limits (keep first ~3000 chars)
    truncated = raw_text[:3000]

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": SUMMARY_PROMPT.format(report_text=truncated)}],
            temperature=0.1,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in LLM response: {raw[:200]}")
        return json.loads(match.group())

    except Exception as e:
        logger.error(f"Report summarisation LLM error: {e}")
        return {
            "error": f"LLM summarisation failed: {str(e)[:200]}",
            "patient_friendly_summary": "Could not automatically summarise this report. Please review the raw text.",
        }


# ── Public Entry Point ─────────────────────────────────────────────────────

def process_medical_report(file_bytes: bytes, filename: str) -> dict:
    """
    Full pipeline: extract text → summarise → return structured dict.
    Dict matches ReportSummaryResponse schema.
    """
    # 1. Extract
    try:
        raw_text = extract_text(file_bytes, filename)
    except Exception as e:
        return {"error": str(e), "raw_text": None}

    if not raw_text:
        return {"error": "No text could be extracted from the file.", "raw_text": ""}

    # 2. Summarise
    summary = summarise_report(raw_text)

    # 3. Merge raw_text into response
    summary["raw_text"] = raw_text
    return summary
