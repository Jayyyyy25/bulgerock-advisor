"""
Bulk upsert logic for holdings data.
Uses PostgreSQL ON CONFLICT to handle re-ingestion of the same date's data.
"""
import pandas as pd
from sqlalchemy import text
from .db_client import engine

UPSERT_SQL = """
INSERT INTO holdings
    (client_id, ticker, security_name, isin, asset_class, sector,
     account_type, quantity, market_value, custodian, as_of_date)
VALUES
    (:client_id, :ticker, :security_name, :isin, :asset_class, :sector,
     :account_type, :quantity, :market_value, :custodian, :as_of_date)
ON CONFLICT (client_id, ticker, account_type, as_of_date)
DO UPDATE SET
    security_name = EXCLUDED.security_name,
    isin          = EXCLUDED.isin,
    asset_class   = EXCLUDED.asset_class,
    sector        = EXCLUDED.sector,
    quantity      = EXCLUDED.quantity,
    market_value  = EXCLUDED.market_value,
    custodian     = EXCLUDED.custodian,
    ingested_at   = NOW();
"""


def upsert_holdings(df: pd.DataFrame) -> int:
    """Upsert a canonical holdings DataFrame into the holdings table."""
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    if not records:
        return 0
    with engine.begin() as conn:
        conn.execute(text(UPSERT_SQL), records)
    return len(records)
