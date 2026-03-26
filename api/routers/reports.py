"""
Report generation and download endpoints.
"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import PROCESSED_DIR, REPORTS_DIR
from portfolio.report_generator import ReportGenerator

router = APIRouter()

_report_generator = None


def get_report_generator() -> ReportGenerator:
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


@router.post("/{portfolio_id}")
def generate_report(portfolio_id: str):
    """Generate a one-page Markdown portfolio summary."""
    path = PROCESSED_DIR / f"{portfolio_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Portfolio '{portfolio_id}' not found.")

    client_data = json.loads(path.read_text())
    report_path = get_report_generator().generate_markdown(client_data)
    filename = Path(report_path).name
    return {
        "message":      "Report generated.",
        "portfolio_id": portfolio_id,
        "report_file":  filename,
        "download_url": f"/api/reports/download/{filename}",
    }


@router.get("/download/{filename}")
def download_report(filename: str):
    """Download a generated Markdown report."""
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(str(path), filename=filename, media_type="text/markdown")
