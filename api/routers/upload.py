"""
PDF upload endpoint.
Processes a custodian PDF → saves top_10 summary JSON (for the web UI)
→ upserts full holdings into PostgreSQL (for the Slack bot).
"""
import json
import os
import shutil
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import PROCESSED_DIR, RAW_DIR
from ingestion.portfolio_ingestor import ingest_portfolio
from portfolio.ai_parser import AIPortfolioParser
from portfolio.analytics import PortfolioAnalytics
from portfolio.cross_portfolio import CrossPortfolioAnalyzer

router = APIRouter()

_cross_portfolio: Optional[CrossPortfolioAnalyzer] = None


def get_cross_portfolio() -> CrossPortfolioAnalyzer:
    global _cross_portfolio
    if _cross_portfolio is None:
        _cross_portfolio = CrossPortfolioAnalyzer()
    return _cross_portfolio


@router.post("")
async def upload_pdf(
    file: UploadFile = File(...),
    zoho_client_id: Optional[str] = Form(default=None),
    as_of_date: Optional[str] = Form(default=None),
):
    """
    Upload a custodian PDF statement.

    - **file**: PDF file
    - **zoho_client_id**: The Zoho CRM Client_ID this statement belongs to (e.g. CLI001)
    - **as_of_date**: Statement date in YYYY-MM-DD format (defaults to today)
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Parse as_of_date
    try:
        parsed_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="as_of_date must be YYYY-MM-DD format.")

    # Save PDF to data/raw/
    save_path = RAW_DIR / file.filename
    with open(save_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # Extract holdings DataFrame
    parser = AIPortfolioParser()
    df = parser.process_pdf(str(save_path))
    if df.empty:
        raise HTTPException(status_code=422, detail="Could not extract portfolio data from the PDF.")

    # Generate summary (top_10 for web UI JSON)
    analytics = PortfolioAnalytics(df)
    summary = analytics.generate_summary()

    # Save JSON for the web UI
    stem = os.path.splitext(file.filename)[0]
    portfolio_id = f"{stem}_Client"
    client_record = {"client_id": portfolio_id, "zoho_client_id": zoho_client_id,
                     "source_file": file.filename, **summary}
    json_path = PROCESSED_DIR / f"{portfolio_id}.json"
    json_path.write_text(json.dumps(client_record, indent=2, default=str))

    # Derive custodian name from filename
    custodian = stem.replace("_", " ").strip()

    # Ingest full holdings into PostgreSQL (only if a Zoho client ID is provided)
    rows_upserted = 0
    if zoho_client_id:
        rows_upserted = ingest_portfolio(
            df=df,
            client_id=zoho_client_id,
            as_of_date=parsed_date,
            custodian=custodian,
        )

    # Refresh cross-portfolio index
    get_cross_portfolio().reload()

    return {
        "message":         "PDF processed successfully.",
        "portfolio_id":    portfolio_id,
        "zoho_client_id":  zoho_client_id,
        "as_of_date":      str(parsed_date),
        "holdings_extracted": len(df),
        "holdings_in_db":  rows_upserted,
        "total_value":     summary["total_value"],
    }
