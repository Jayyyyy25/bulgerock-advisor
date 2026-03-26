"""
Pocket IA FastAPI backend.

Run with:
    uvicorn api.main:app --reload --port 8000
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .routers import clients, portfolio, policies, upload, analysis, reports

load_dotenv()

app = FastAPI(
    title="Pocket IA API",
    description="Wealth Management API — client data, portfolio analytics, and PDF ingestion.",
    version="2.0.0",
)

ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing data endpoints (PostgreSQL + Zoho)
app.include_router(clients.router,   prefix="/api/clients",   tags=["clients"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(policies.router,  prefix="/api/policies",  tags=["policies"])

# Portfolio processing endpoints (PDF upload, analytics, reports)
app.include_router(upload.router,    prefix="/api/upload",    tags=["upload"])
app.include_router(analysis.router,  prefix="/api/analysis",  tags=["analysis"])
app.include_router(reports.router,   prefix="/api/reports",   tags=["reports"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "pocket-ia-api", "version": "2.0.0"}
