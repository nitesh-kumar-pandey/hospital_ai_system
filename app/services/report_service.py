"""
Medical Report Summarisation Service
Supports: PDF (text-based OR scanned/symbol-font), PNG/JPG images, plain text

Extraction strategy for PDFs:
  1. Try PyMuPDF text extraction.
  2. If the extracted text is empty or >60 % Private-Use-Area (symbol-font)
     characters, fall back to rendering every page as a 250-dpi PNG image
     and running pytesseract OCR on each one.
  3. Plain text / image files are handled directly.
"""

import io
import os
import re
import json
from pathlib import Path

from app.utils.logger import get_logger
from groq import Groq

logger     = get_logger(__name__)
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama3-8b-8192")
client     = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ── Helpers ────────────────────────────────────────────────────────────────

def _is_garbled(text: str) -> bool:
    """
    Return True when the extracted text is mostly Private-Use-Area Unicode
    (0xE000–0xF8FF), which happens with symbol/icon fonts used in many
    lab-report PDFs.  A threshold of 40 % PUA chars signals garbling.
    """
    if not text:
        return True
    pua = sum(1 for ch in text if "\ue000" <= ch <= "\uf8ff")
    return (pua / len(text)) > 0.40


def _ocr_pdf_pages(file_bytes: bytes) -> str:
    """
    Render every PDF page as a 250-dpi image and OCR with pytesseract.
    Returns concatenated text from all pages.
    """
    try:
        import fitz                          # PyMuPDF
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            f"Missing dependency for OCR fallback: {exc}.\n"
            "Run: pip install pymupdf pytesseract Pillow --break-system-packages\n"
            "Also install the Tesseract binary: https://github.com/tesseract-ocr/tesseract"
        )

    doc    = fitz.open(stream=file_bytes, filetype="pdf")
    # 250 dpi ≈ scale factor 250/72
    mat    = fitz.Matrix(250 / 72, 250 / 72)
    pages  = []

    for page_num, page in enumerate(doc):
        pix       = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        img       = Image.open(io.BytesIO(img_bytes))
        page_text = pytesseract.image_to_string(img, lang="eng")
        pages.append(page_text)
        logger.info(f"OCR page {page_num + 1}: {len(page_text)} chars")

    doc.close()
    return "\n\n".join(pages).strip()


# ── Text Extraction ────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract readable text from a PDF.
    First tries PyMuPDF's native text layer; if the result is empty or
    garbled (symbol-font PDFs), falls back to page-render + OCR.
    """
    try:
        import fitz
    except ImportError:
        raise RuntimeError(
            "PyMuPDF not installed. Run: pip install pymupdf --break-system-packages"
        )

    doc        = fitz.open(stream=file_bytes, filetype="pdf")
    pages_text = [page.get_text() for page in doc]
    doc.close()

    raw = "\n".join(pages_text).strip()
    logger.info(f"PyMuPDF extracted {len(raw)} chars from {len(pages_text)} page(s)")

    if _is_garbled(raw):
        logger.warning(
            "Extracted text is garbled (symbol/private-use-area font detected). "
            "Falling back to page-render + OCR."
        )
        raw = _ocr_pdf_pages(file_bytes)
        logger.info(f"OCR fallback produced {len(raw)} chars")

    return raw


def extract_text_from_image(file_bytes: bytes) -> str:
    """OCR a raster image (PNG / JPG / BMP / TIFF) using pytesseract."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "pytesseract or Pillow not installed.\n"
            "Run: pip install pytesseract Pillow --break-system-packages\n"
            "Also install Tesseract: https://github.com/tesseract-ocr/tesseract"
        )

    image = Image.open(io.BytesIO(file_bytes))
    text  = pytesseract.image_to_string(image, lang="eng")
    logger.info(f"Image OCR extracted {len(text)} chars")
    return text.strip()


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route extraction by file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        return extract_text_from_image(file_bytes)
    if ext in (".txt", ".md"):
        return file_bytes.decode("utf-8", errors="ignore").strip()
    raise ValueError(
        f"Unsupported file type: '{ext}'. Supported: pdf, png, jpg, bmp, tiff, txt"
    )


# ── LLM Summarisation ─────────────────────────────────────────────────────

SUMMARY_PROMPT = """You are a medical AI assistant. A medical lab/diagnostic report has been uploaded.
Extract key information and produce a patient-friendly summary.

REPORT TEXT:
\"\"\"
{report_text}
\"\"\"

Respond ONLY with a valid JSON object — no markdown, no code fences, no extra text:
{{
  "patient_name": "<string or null>",
  "age": "<string or null>",
  "diagnosis": ["<diagnosis 1>", "..."],
  "symptoms": ["<observed finding or concern>", "..."],
  "medications": ["<drug name + dosage if any>", "..."],
  "lab_results": {{
    "<test name>": "<result value + unit + normal range if available>"
  }},
  "doctor_notes": "<string or null>",
  "recommendations": ["<actionable recommendation>", "..."],
  "patient_friendly_summary": "<2-4 plain-English sentences a patient can understand>",
  "urgency_flag": "Critical|Watch|Normal"
}}

Urgency rules:
- Critical : life-threatening values (e.g. troponin elevated, SpO2 <88 %, severe anaemia, dangerously high/low glucose)
- Watch    : results outside reference range needing follow-up (e.g. borderline cholesterol, hsCRP ≥1, HbA1c 5.7–6.4 %)
- Normal   : all values within reference ranges

Important:
- Extract EVERY test result mentioned, including those with missing numeric values — note them as "Result pending" or "Not reported".
- Use empty list [] or null if a field has no data — do NOT invent data.
- patient_friendly_summary must avoid medical jargon and explain what the results mean for the patient.
"""

def summarise_report(raw_text: str) -> dict:
    """Send extracted text to Groq LLM and return a structured summary dict."""
    if not raw_text or len(raw_text.strip()) < 20:
        return {"error": "Report text is too short or empty to summarise."}

    # Send up to ~4 000 chars (covers most 6-page reports after OCR)
    truncated = raw_text[:4000]

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{
                "role": "user",
                "content": SUMMARY_PROMPT.format(report_text=truncated),
            }],
            temperature=0.1,
            max_tokens=1200,
        )
        raw_llm = response.choices[0].message.content.strip()

        # Strip markdown code fences if the model added them
        raw_llm = re.sub(r"^```(?:json)?\s*", "", raw_llm)
        raw_llm = re.sub(r"\s*```$", "", raw_llm)

        match = re.search(r"\{.*\}", raw_llm, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object found in LLM response: {raw_llm[:300]}")

        return json.loads(match.group())

    except Exception as exc:
        logger.error(f"Report summarisation LLM error: {exc}")
        return {
            "error": f"LLM summarisation failed: {str(exc)[:300]}",
            "patient_friendly_summary": (
                "Could not automatically summarise this report. "
                "Please review the raw extracted text below."
            ),
        }


# ── Public Entry Point ─────────────────────────────────────────────────────

def process_medical_report(file_bytes: bytes, filename: str) -> dict:
    """
    Full pipeline: extract text → LLM summarise → return structured dict
    matching the ReportSummaryResponse schema.
    """
    # 1. Extract text
    try:
        raw_text = extract_text(file_bytes, filename)
    except Exception as exc:
        return {"error": str(exc), "raw_text": None}

    if not raw_text:
        return {
            "error": "No text could be extracted from this file.",
            "raw_text": "",
        }

    logger.info(f"Total extracted text: {len(raw_text)} chars — sending to LLM")

    # 2. LLM summarise
    summary = summarise_report(raw_text)

    # 3. Always attach raw_text so the UI can show it in the expander
    summary["raw_text"] = raw_text
    return summary