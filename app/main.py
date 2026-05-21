from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.patient_routes import router
from app.services.db_services import init_db



app = FastAPI(
     title="🏥 AI Hospital Resource Allocation",
     description="LLM-powered patient triage and resource management system.",
     version="1.0.0",
)

app.add_middleware(
     CORSMiddleware,
     allow_origins=["*"],
     allow_methods=["*"],
     allow_headers=["*"],
)

@app.on_event("startup")
def startup():
     init_db()

app.include_router(router)

@app.get("/health")
def health():
     return {"status": "ok"}