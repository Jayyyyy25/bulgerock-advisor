"""
Seed script: creates mock clients in Zoho CRM and mock policies in PostgreSQL.
Run once: python scripts/seed_mock_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from sqlalchemy import text
from ingestion.db_client import engine
from agent_tools.zoho_client import create_contact

# ---------------------------------------------------------------------------
# Mock clients to create in Zoho CRM
# ---------------------------------------------------------------------------
MOCK_CLIENTS = [
    {
        "first_name": "East",
        "last_name": "Asia",
        "client_id": "CLI001",
        "risk_profile": "Moderate",
        "aum": 15760701.10,
        "investment_objectives": "Portfolio targeting balanced growth with moderate risk. Primary allocations: Equities (58.3%), Fixed Income (22.1%), Cash (12.4%). Geographic focus: China.",
        "last_meeting_date": "2026-03-27",
    },
    {
        "first_name": "Euro",
        "last_name": "Alpine",
        "client_id": "CLI002",
        "risk_profile": "Conservative",
        "aum": 10255791.93,
        "investment_objectives": "Portfolio targeting capital preservation and income generation. Primary allocations: Fixed Income (61.4%), Cash (18.7%), Equities (14.2%). Geographic focus: Europe.",
        "last_meeting_date": "2026-03-27",
    },
    {
        "first_name": "Family",
        "last_name": "Office",
        "client_id": "CLI003",
        "risk_profile": "Moderate",
        "aum": 20596240.22,
        "investment_objectives": "Portfolio targeting balanced growth with moderate risk. Primary allocations: Equities (42.1%), Fixed Income (28.3%), Alternatives (18.5%). Geographic focus: Global.",
        "last_meeting_date": "2026-03-27",
    },
    {
        "first_name": "Gulf",
        "last_name": "Capital",
        "client_id": "CLI004",
        "risk_profile": "Aggressive",
        "aum": 14340530.00,
        "investment_objectives": "Portfolio targeting long-term capital appreciation. Primary allocations: Equities (52.6%), Alternatives (24.3%), Fixed Income (14.1%). Geographic focus: Global.",
        "last_meeting_date": "2026-03-27",
    },
    {
        "first_name": "Indian",
        "last_name": "Custodian",
        "client_id": "CLI005",
        "risk_profile": "Moderate",
        "aum": 235278752.00,
        "investment_objectives": "Portfolio targeting balanced growth with moderate risk. Primary allocations: Equities (49.8%), Fixed Income (31.2%), Cash (11.5%). Geographic focus: India.",
        "last_meeting_date": "2026-03-27",
    },
    {
        "first_name": "Northern",
        "last_name": "Trust",
        "client_id": "CLI006",
        "risk_profile": "Conservative",
        "aum": 11308155.68,
        "investment_objectives": "Portfolio targeting capital preservation and income generation. Primary allocations: Fixed Income (54.2%), Cash (21.8%), Equities (17.3%). Geographic focus: USA.",
        "last_meeting_date": "2026-03-27",
    },
    {
        "first_name": "Pacific",
        "last_name": "Bridge",
        "client_id": "CLI007",
        "risk_profile": "Aggressive",
        "aum": 6232608.50,
        "investment_objectives": "Portfolio targeting long-term capital appreciation. Primary allocations: Equities (63.5%), Alternatives (19.2%), Fixed Income (11.8%). Geographic focus: Japan.",
        "last_meeting_date": "2026-03-27",
    },
]

# ---------------------------------------------------------------------------
# Mock policies to insert into PostgreSQL
# ---------------------------------------------------------------------------
MOCK_POLICIES = [
    # CLI001 — East Asia
    ("POL-EA-001", "CLI001", "Life Insurance",     "Manulife",       5000000.00, 13400.00, "2026-09-30", "Term Life (20-year)"),
    ("POL-EA-002", "CLI001", "Medical Insurance",  "Great Eastern",   600000.00,  5200.00, "2026-07-01", "Hospitalisation & Surgical"),
    # CLI002 — Euro Alpine
    ("POL-EU-001", "CLI002", "Life Insurance",     "Zurich Life",    6000000.00, 15800.00, "2026-10-31", "Universal Life"),
    ("POL-EU-002", "CLI002", "Health Insurance",   "Swiss Life",      400000.00,  6100.00, "2027-02-28", "International Health Plan"),
    ("POL-EU-003", "CLI002", "Property Insurance", "AXA",             900000.00,  2800.00, "2026-12-31", "Buildings & Contents"),
    # CLI003 — Family Office
    ("POL-FO-001", "CLI003", "Life Insurance",     "Prudential",    15000000.00, 31000.00, "2026-10-01", "Whole Life"),
    ("POL-FO-002", "CLI003", "Health Insurance",   "Swiss Life",      500000.00,  7200.00, "2027-02-01", "International Health Plan"),
    ("POL-FO-003", "CLI003", "Property Insurance", "Zurich Life",    2000000.00,  4500.00, "2026-08-31", "Buildings & Contents"),
    # CLI004 — Gulf Capital
    ("POL-GC-001", "CLI004", "Life Insurance",     "MetLife",        8000000.00, 19200.00, "2026-09-15", "Whole Life"),
    ("POL-GC-002", "CLI004", "Medical Insurance",  "AIA",             800000.00,  8400.00, "2026-12-01", "Comprehensive Health Plan"),
    # CLI005 — Indian Custodian
    ("POL-IN-001", "CLI005", "Life Insurance",     "HDFC Life",      4000000.00, 10800.00, "2026-12-31", "Term Life (30-year)"),
    ("POL-IN-002", "CLI005", "Critical Illness",   "Max Life",        750000.00,  3400.00, "2027-03-15", "Critical Illness (60 Conditions)"),
    ("POL-IN-003", "CLI005", "Personal Accident",  "Bajaj Allianz",   500000.00,  1300.00, "2026-06-30", "Personal Accident & Disability"),
    # CLI006 — Northern Trust
    ("POL-NT-001", "CLI006", "Life Insurance",     "Prudential",    10000000.00, 22500.00, "2026-11-30", "Whole Life"),
    ("POL-NT-002", "CLI006", "Critical Illness",   "AIA",            2000000.00,  6800.00, "2026-08-15", "Critical Illness (60 Conditions)"),
    ("POL-NT-003", "CLI006", "Property Insurance", "Aviva",          1500000.00,  3200.00, "2027-01-15", "Buildings & Contents"),
    # CLI007 — Pacific Bridge
    ("POL-PB-001", "CLI007", "Life Insurance",     "AIA",            5500000.00, 14600.00, "2026-11-15", "Term Life (25-year)"),
    ("POL-PB-002", "CLI007", "Critical Illness",   "Manulife",        900000.00,  3900.00, "2027-01-31", "Critical Illness (36 Conditions)"),
]


def seed_zoho_clients():
    print("\n=== Creating clients in Zoho CRM ===")
    for c in MOCK_CLIENTS:
        try:
            result = create_contact(**c)
            status = result.get("status", "unknown")
            details = result.get("details", {})
            zoho_id = details.get("id", "—")
            print(f"  {c['client_id']} {c['first_name']} {c['last_name']}: {status} (zoho_id={zoho_id})")
        except Exception as e:
            print(f"  {c['client_id']} FAILED: {e}")


def seed_postgres_policies():
    print("\n=== Inserting policies into PostgreSQL ===")

    # Ensure coverage_type column exists
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE policies ADD COLUMN IF NOT EXISTS coverage_type VARCHAR(100)"
        ))

    sql = text("""
        INSERT INTO policies
            (policy_id, client_id, policy_type, insurer, coverage_amount,
             premium, renewal_date, coverage_type, status)
        VALUES
            (:policy_id, :client_id, :policy_type, :insurer, :coverage_amount,
             :premium, :renewal_date, :coverage_type, 'active')
        ON CONFLICT (policy_id) DO UPDATE SET
            coverage_type = EXCLUDED.coverage_type,
            premium       = EXCLUDED.premium,
            renewal_date  = EXCLUDED.renewal_date
    """)

    rows = [
        {
            "policy_id":       p[0],
            "client_id":       p[1],
            "policy_type":     p[2],
            "insurer":         p[3],
            "coverage_amount": p[4],
            "premium":         p[5],
            "renewal_date":    p[6],
            "coverage_type":   p[7],
        }
        for p in MOCK_POLICIES
    ]

    with engine.begin() as conn:
        for row in rows:
            conn.execute(sql, row)
            print(f"  {row['policy_id']} ({row['client_id']}) — {row['coverage_type']}: OK")


if __name__ == "__main__":
    seed_zoho_clients()
    seed_postgres_policies()
    print("\nDone.")
