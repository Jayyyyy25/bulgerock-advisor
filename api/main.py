"""
Pocket IA FastAPI backend.

Run with:
    uvicorn api.main:app --reload --port 8000
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .routers import clients, portfolio, policies

load_dotenv()

app = FastAPI(
    title="Pocket IA API",
    description="Wealth Management data API powering the Client 360 dashboard.",
    version="1.0.0",
)

ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(clients.router,   prefix="/api/clients",   tags=["clients"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(policies.router,  prefix="/api/policies",  tags=["policies"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "pocket-ia-api"}
