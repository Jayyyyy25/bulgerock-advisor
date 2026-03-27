"""
PDF upload endpoint.
- Always re-processes: clears existing data for the portfolio_name, then ingests fresh.
- After saving, creates/updates a Zoho CRM contact for the portfolio owner.
"""
import os
import shutil
from datetime import date, datetime
from typing import Annotated, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import text

from config import RAW_DIR
from ingestion.portfolio_ingestor import (
    ingest_portfolio,
    save_portfolio_snapshot,
)
from ingestion.db_client import engine
from portfolio.ai_parser import AIPortfolioParser
from portfolio.analytics import PortfolioAnalytics
from agent_tools.zoho_client import upsert_contact

router = APIRouter()


def _delete_portfolio_data(portfolio_name: str) -> bool:
    """
    Delete all holdings and snapshots for a portfolio.
    Returns True if anything was deleted, False if portfolio didn't exist.
    """
    with engine.begin() as conn:
        # Get the client_id before deleting snapshots
        row = conn.execute(
            text("SELECT zoho_client_id FROM portfolio_snapshots WHERE portfolio_name = :n LIMIT 1"),
            {"n": portfolio_name},
        ).fetchone()

        if not row:
            return False

        client_id = row[0]
        conn.execute(text("DELETE FROM holdings WHERE client_id = :cid"), {"cid": client_id})
        conn.execute(text("DELETE FROM portfolio_snapshots WHERE portfolio_name = :n"), {"n": portfolio_name})
        return True


def _get_or_assign_client_id(portfolio_name: str) -> str:
    """
    Return the existing CLI ID for this portfolio name if already in DB,
    otherwise assign the next available CLIxxx ID.
    """
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT zoho_client_id FROM portfolio_snapshots WHERE portfolio_name = :n LIMIT 1"),
            {"n": portfolio_name},
        ).fetchone()
        if row and row[0]:
            return row[0]

        # Count existing CLI-style IDs to assign next number
        result = conn.execute(
            text("SELECT COUNT(DISTINCT zoho_client_id) FROM portfolio_snapshots WHERE zoho_client_id ~ '^CLI[0-9]+$'")
        ).fetchone()
        next_num = (result[0] if result else 0) + 1
        return f"CLI{next_num:03d}"


def _infer_risk_profile(risk_metrics: dict) -> str:
    """Classify risk profile from estimated volatility."""
    vol = risk_metrics.get("estimated_volatility_pct", 0) or 0
    if vol < 8:
        return "Conservative"
    elif vol < 15:
        return "Moderate"
    else:
        return "Aggressive"


def _build_investment_objectives(summary: dict) -> str:
    """Generate a plain-English objectives sentence from asset allocation."""
    alloc: dict = summary.get("asset_allocation", {})
    if not alloc:
        return "Diversified investment strategy across multiple asset classes."

    top = sorted(alloc.items(), key=lambda x: x[1], reverse=True)[:3]
    top_str = ", ".join(f"{k} ({v:.1f}%)" for k, v in top)

    geo: dict = summary.get("geographic_exposure", {})
    top_geo = max(geo, key=geo.get) if geo else "Global"

    risk = _infer_risk_profile(summary.get("risk_metrics", {}))
    risk_desc = {
        "Conservative": "capital preservation and income generation",
        "Moderate":     "balanced growth with moderate risk",
        "Aggressive":   "long-term capital appreciation",
    }[risk]

    return (
        f"Portfolio targeting {risk_desc}. "
        f"Primary allocations: {top_str}. "
        f"Geographic focus: {top_geo}."
    )


@router.post("")
async def upload_pdf(
    file: UploadFile = File(...),
    portfolio_name: Annotated[Optional[str], Form()] = None,
    as_of_date: Annotated[Optional[str], Form()] = None,
    zoho_client_id: Annotated[Optional[str], Form()] = None,
):
    """
    Upload a custodian PDF statement.

    - **file**: PDF file
    - **portfolio_name**: Stable name for this portfolio across periods (e.g. "Northern Trust")
    - **as_of_date**: Statement date YYYY-MM-DD (defaults to today)
    - **zoho_client_id**: Optional Zoho CRM Client_ID to link holdings
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    try:
        parsed_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="as_of_date must be YYYY-MM-DD format.")

    # Save PDF to data/raw/
    save_path = RAW_DIR / file.filename
    with open(save_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    parser = AIPortfolioParser()

    # Auto-detect portfolio name from PDF if not provided
    if not portfolio_name or not portfolio_name.strip():
        portfolio_name = parser.extract_portfolio_name(str(save_path))

    # Clear existing data for this portfolio so the upload is a clean replace
    _delete_portfolio_data(portfolio_name)

    # Parse PDF → full holdings DataFrame
    try:
        df = parser.process_pdf(str(save_path))
    except RuntimeError as e:
        err = str(e)
        if "rate_limit" in err.lower() or "429" in err:
            raise HTTPException(status_code=429, detail="Claude API rate limit reached. Please wait a moment and try again.")
        if "authentication" in err.lower() or "401" in err or "invalid x-api-key" in err.lower():
            raise HTTPException(status_code=401, detail=f"Claude API key invalid or expired — check ANTHROPIC_API_KEY in .env. Detail: {err}")
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF parsing error: {e}")

    if df.empty:
        raise HTTPException(status_code=422, detail="No holdings extracted — PDF may be image-based or not a supported statement format.")

    # Compute derived analytics
    analytics = PortfolioAnalytics(df)
    summary = analytics.generate_summary()
    custodian = os.path.splitext(file.filename)[0].replace("_", " ").strip()

    # Derive client_id — use provided zoho_client_id or assign next CLI ID
    client_id = zoho_client_id or _get_or_assign_client_id(portfolio_name)

    # Persist derived analytics → portfolio_snapshots
    save_portfolio_snapshot(
        portfolio_name=portfolio_name,
        as_of_date=parsed_date,
        summary=summary,
        zoho_client_id=client_id,
        source_file=file.filename,
    )

    # Persist raw holdings → holdings table
    rows_upserted = ingest_portfolio(
        df=df,
        client_id=client_id,
        as_of_date=parsed_date,
        custodian=custodian,
    )

    # Build Zoho contact attributes from analytics (mock what can't be derived)
    name_parts = portfolio_name.strip().split()
    first_name = " ".join(name_parts[:-1]) if len(name_parts) > 1 else portfolio_name
    last_name  = name_parts[-1] if len(name_parts) > 1 else "Portfolio"

    risk_profile          = _infer_risk_profile(summary.get("risk_metrics", {}))
    investment_objectives = _build_investment_objectives(summary)
    aum                   = float(summary.get("total_value") or 0)
    last_meeting_date     = str(date.today())  # date PDF was uploaded

    # Create Zoho contact (skips if Client_ID already exists)
    zoho_result = {}
    try:
        zoho_result = upsert_contact(
            client_id=client_id,
            first_name=first_name,
            last_name=last_name,
            risk_profile=risk_profile,
            aum=aum,
            investment_objectives=investment_objectives,
            last_meeting_date=last_meeting_date,
        )
    except Exception as e:
        zoho_result = {"status": "error", "detail": str(e)}

    return {
        "message":            "PDF processed and stored successfully.",
        "client_id":          portfolio_name,
        "portfolio_name":     portfolio_name,
        "zoho_client_id":     client_id,
        "zoho_status":        zoho_result.get("status", "unknown"),
        "as_of_date":         str(parsed_date),
        "holdings_extracted": len(df),
        "holdings_in_db":     rows_upserted,
        "total_value":        aum,
        "risk_profile":       risk_profile,
        "skipped":            False,
    }


@router.delete("/{portfolio_name}")
def delete_portfolio(portfolio_name: str):
    """Delete all holdings and snapshots for a portfolio."""
    deleted = _delete_portfolio_data(portfolio_name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Portfolio '{portfolio_name}' not found.")
    return {"message": f"Portfolio '{portfolio_name}' deleted.", "portfolio_name": portfolio_name}
