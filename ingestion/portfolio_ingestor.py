"""
Ingests a portfolio DataFrame (produced by AIPortfolioParser) into the PostgreSQL holdings table.
Called after every PDF upload — the JSON stores top_10 for the web UI,
this stores the full holdings for the Slack bot's query_portfolio tool.
"""
from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import text

from ingestion.db_client import engine


def ingest_portfolio(
    df: pd.DataFrame,
    client_id: str,
    as_of_date: Optional[date] = None,
    custodian: Optional[str] = None,
) -> int:
    """
    Upsert all holdings rows into PostgreSQL.

    Args:
        df:          Full holdings DataFrame from AIPortfolioParser.
        client_id:   Zoho Client_ID (e.g. "CLI001") that owns these holdings.
        as_of_date:  Statement date. Defaults to today.
        custodian:   Custodian name derived from the source PDF filename.

    Returns:
        Number of rows upserted.
    """
    if df.empty:
        return 0

    as_of_date = as_of_date or date.today()

    upsert_sql = text("""
        INSERT INTO holdings
            (client_id, ticker, security_name, isin, asset_class, sector, geography,
             account_type, quantity, market_value, currency, custodian, as_of_date)
        VALUES
            (:client_id, :ticker, :security_name, :isin, :asset_class, :sector, :geography,
             :account_type, :quantity, :market_value, :currency, :custodian, :as_of_date)
        ON CONFLICT (client_id, security_name, account_type, as_of_date)
        DO UPDATE SET
            ticker       = EXCLUDED.ticker,
            isin         = EXCLUDED.isin,
            asset_class  = EXCLUDED.asset_class,
            sector       = EXCLUDED.sector,
            geography    = EXCLUDED.geography,
            quantity     = EXCLUDED.quantity,
            market_value = EXCLUDED.market_value,
            currency     = EXCLUDED.currency,
            custodian    = EXCLUDED.custodian,
            ingested_at  = NOW()
    """)

    rows = []
    for _, row in df.iterrows():
        security_name = str(row.get("security_name") or "").strip()
        if not security_name:
            continue

        isin = row.get("isin")
        isin = str(isin).strip() if isin and str(isin).lower() not in ("none", "nan", "") else None

        # Use ISIN as ticker if available, otherwise abbreviate security name
        ticker = isin or security_name[:20]

        rows.append({
            "client_id":     client_id,
            "ticker":        ticker,
            "security_name": security_name,
            "isin":          isin,
            "asset_class":   row.get("asset_class"),
            "sector":        row.get("sector"),
            "geography":     row.get("geography"),
            "account_type":  "Managed Portfolio",
            "quantity":      row.get("quantity"),
            "market_value":  row.get("market_value"),
            "currency":      "USD",
            "custodian":     custodian,
            "as_of_date":    as_of_date,
        })

    if not rows:
        return 0

    with engine.begin() as conn:
        conn.execute(upsert_sql, rows)

    return len(rows)
