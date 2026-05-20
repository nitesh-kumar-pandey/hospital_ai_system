# 🏥 AI Hospital Resource Allocation System

A production-ready AI-powered hospital triage and resource management system using **LangGraph**, **FastAPI**, and **Streamlit**.

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                           │
│   Admit Patient │ Patient Queue │ Dashboard                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP (REST)
┌────────────────────────▼────────────────────────────────────────┐
│                     FastAPI Backend                              │
│   POST /api/v1/allocate  │  GET /api/v1/patients                │
│   POST /api/v1/discharge │  GET /api/v1/resources               │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   LangGraph Workflow                             │
│                                                                  │
│  [Intake] → [Priority AI (Claude)] → [Resource] → [Optimizer]   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   SQLite / PostgreSQL                            │
│        Beds │ Doctors │ Patients                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo>
cd hospital_ai_system
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run Backend (FastAPI)

```bash
cd hospital_ai_system
uvicorn app.main:app --reload --port 8000
```

### 4. Run Frontend (Streamlit) — in a new terminal

```bash
cd hospital_ai_system
streamlit run frontend/streamlit_app.py
```

### 5. Open Browser

- **Streamlit UI:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs

---

## 🗂️ Project Structure

```
hospital_ai_system/
├── app/
│   ├── main.py                    # FastAPI entrypoint + CORS
│   ├── routes/
│   │   └── patient_routes.py      # REST endpoints
│   ├── graph/
│   │   ├── state.py               # TypedDict for LangGraph state
│   │   ├── workflow.py            # Graph definition + singleton
│   │   └── nodes/
│   │       ├── intake.py          # Input validation & normalization
│   │       ├── priority.py        # Claude AI triage engine
│   │       ├── resource.py        # Resource DB fetch
│   │       └── optimizer.py       # Bed/doctor assignment logic
│   ├── services/
│   │   └── db_service.py          # SQLite with thread-safe locking
│   ├── models/
│   │   └── schemas.py             # Pydantic request/response models
│   └── utils/
│       └── logger.py              # Structured logging
├── frontend/
│   └── streamlit_app.py           # Full Streamlit UI
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🧠 How It Works

### LangGraph Pipeline

1. **Intake Node** — Validates and normalizes patient data, assigns UUID, timestamps.
2. **Priority Node (Claude AI)** — Sends symptoms + vitals to Claude, gets structured JSON with `priority_level`, `priority_score`, and `reasoning`. Falls back to rule-based scoring if LLM fails.
3. **Resource Node** — Fetches live counts of available ICU beds, general beds, and doctors from the database.
4. **Optimizer Node** — Atomically allocates the best available bed and doctor based on priority. Handles waiting queue if no resources are free.

### Priority Levels

| Level    | Score  | Action                            |
|----------|--------|-----------------------------------|
| Critical | 85–100 | ICU assignment, immediate         |
| High     | 60–84  | General ward, urgent              |
| Medium   | 35–59  | General ward, semi-urgent         |
| Low      | 1–34   | Outpatient queue                  |

---

## 🌐 API Reference

### `POST /api/v1/allocate`
Admit and triage a patient.

```json
{
  "patient_name": "John Doe",
  "age": 55,
  "symptoms": "Chest pain, shortness of breath",
  "vitals": {
    "heart_rate": 115,
    "systolic_bp": 170,
    "spo2": 93,
    "temperature": 99.1
  }
}
```

### `GET /api/v1/patients`
List all patients.

### `POST /api/v1/discharge/{patient_id}`
Discharge patient and free bed/doctor.

### `GET /api/v1/resources`
Get current resource counts.

---

## 🔒 Production Upgrades

| Component | Dev (current) | Production |
|-----------|--------------|------------|
| Database  | SQLite       | PostgreSQL |
| Caching   | In-memory    | Redis      |
| Queue     | None         | Kafka / RabbitMQ |
| Auth      | None         | JWT / OAuth2 |
| Logging   | stdout       | ELK Stack  |
| Secrets   | .env file    | AWS Secrets Manager / Vault |

---

## 🛡️ Error Handling

- LLM failure → rule-based priority fallback
- Resource conflict → thread lock on allocation
- Missing fields → validation errors returned before graph runs
- API errors → HTTP 500 with detail message

---

## 📄 License

MIT
