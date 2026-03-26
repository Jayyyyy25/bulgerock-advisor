"""
PDF upload endpoint.
- Checks if (portfolio_name, as_of_date) already exists → returns existing snapshot
- Otherwise: processes PDF → saves raw holdings + derived snapshot to PostgreSQL
"""
import os
import shutil
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import RAW_DIR
from ingestion.portfolio_ingestor import (
    ingest_portfolio,
    save_portfolio_snapshot,
    snapshot_exists,
)
from portfolio.ai_parser import AIPortfolioParser
from portfolio.analytics import PortfolioAnalytics

router = APIRouter()


@router.post("")
async def upload_pdf(
    file: UploadFile = File(...),
    portfolio_name: str = Form(...),
    as_of_date: Optional[str] = Form(default=None),
    zoho_client_id: Optional[str] = Form(default=None),
):
    """
    Upload a custodian PDF statement.

    - **file**: PDF file
    - **portfolio_name**: Stable name for this portfolio across periods (e.g. "Northern Trust")
    - **as_of_date**: Statement date YYYY-MM-DD (defaults to today)
    - **zoho_client_id**: Optional Zoho CRM Client_ID to link holdings (e.g. CLI001)
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    try:
        parsed_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="as_of_date must be YYYY-MM-DD format.")

    # Return existing snapshot without re-processing
    if snapshot_exists(portfolio_name, parsed_date):
        return {
            "message":        "Snapshot already exists — skipped reprocessing.",
            "portfolio_name": portfolio_name,
            "as_of_date":     str(parsed_date),
            "skipped":        True,
        }

    # Save PDF to data/raw/
    save_path = RAW_DIR / file.filename
    with open(save_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # Parse PDF → full holdings DataFrame
    df = AIPortfolioParser().process_pdf(str(save_path))
    if df.empty:
        raise HTTPException(status_code=422, detail="Could not extract portfolio data from the PDF.")

    # Compute derived analytics
    analytics = PortfolioAnalytics(df)
    summary = analytics.generate_summary()
    custodian = os.path.splitext(file.filename)[0].replace("_", " ").strip()

    # Persist derived analytics → portfolio_snapshots
    save_portfolio_snapshot(
        portfolio_name=portfolio_name,
        as_of_date=parsed_date,
        summary=summary,
        zoho_client_id=zoho_client_id,
        source_file=file.filename,
    )

    # Persist raw holdings → holdings table
    rows_upserted = ingest_portfolio(
        df=df,
        client_id=portfolio_name,
        as_of_date=parsed_date,
        custodian=custodian,
    )

    return {
        "message":           "PDF processed and stored successfully.",
        "client_id":         portfolio_name,
        "portfolio_name":    portfolio_name,
        "zoho_client_id":    zoho_client_id,
        "as_of_date":        str(parsed_date),
        "holdings_extracted": len(df),
        "holdings_in_db":    rows_upserted,
        "total_value":       summary["total_value"],
        "skipped":           False,
    }
