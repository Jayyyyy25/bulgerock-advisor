"""FastAPI dependency injection for database sessions."""
from sqlalchemy.orm import Session
from ingestion.db_client import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
