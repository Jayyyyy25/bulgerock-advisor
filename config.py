"""
Shared path configuration for all modules.
Import this instead of hardcoding paths anywhere.
"""
from pathlib import Path

ROOT_DIR      = Path(__file__).parent
DATA_DIR      = ROOT_DIR / "data"
RAW_DIR       = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed_clients"
REPORTS_DIR   = ROOT_DIR / "reports"

# Ensure runtime directories exist
for _dir in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
