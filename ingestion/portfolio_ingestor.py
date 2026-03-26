"""
Ingests portfolio data into PostgreSQL.

- ingest_portfolio()       — raw holdings DataFrame → holdings table
- save_portfolio_snapshot() — derived analytics → portfolio_snapshots table
- snapshot_exists()         — check before re-processing a PDF
"""
import json
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import text

from ingestion.db_client import engine


def snapshot_exists(portfolio_name: str, as_of_date: date) -> bool:
    """Return True if this (portfolio_name, as_of_date) has already been processed."""
    sql = text("""
        SELECT 1 FROM portfolio_snapshots
        WHERE portfolio_name = :portfolio_name AND as_of_date = :as_of_date
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"portfolio_name": portfolio_name, "as_of_date": as_of_date}).first()
    return row is not None


def save_portfolio_snapshot(
    portfolio_name: str,
    as_of_date: date,
    summary: dict,
    zoho_client_id: Optional[str] = None,
    source_file: Optional[str] = None,
) -> None:
    """
    Upsert derived analytics into portfolio_snapshots.
    If a snapshot for (portfolio_name, as_of_date) already exists it is overwritten.
    """
    sql = text("""
        INSERT INTO portfolio_snapshots
            (portfolio_name, zoho_client_id, source_file, as_of_date,
             total_value, asset_allocation, sector_concentration,
             geographic_exposure, top_10_holdings, risk_metrics)
        VALUES
            (:portfolio_name, :zoho_client_id, :source_file, :as_of_date,
             :total_value, CAST(:asset_allocation AS jsonb), CAST(:sector_concentration AS jsonb),
             CAST(:geographic_exposure AS jsonb), CAST(:top_10_holdings AS jsonb), CAST(:risk_metrics AS jsonb))
        ON CONFLICT (portfolio_name, as_of_date)
        DO UPDATE SET
            zoho_client_id       = EXCLUDED.zoho_client_id,
            source_file          = EXCLUDED.source_file,
            total_value          = EXCLUDED.total_value,
            asset_allocation     = EXCLUDED.asset_allocation,
            sector_concentration = EXCLUDED.sector_concentration,
            geographic_exposure  = EXCLUDED.geographic_exposure,
            top_10_holdings      = EXCLUDED.top_10_holdings,
            risk_metrics         = EXCLUDED.risk_metrics,
            ingested_at          = NOW()
    """)

    def _json(val, default):
        """Serialize to JSON, converting numpy types to native Python."""
        class _Enc(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, (np.integer,)): return int(o)
                if isinstance(o, (np.floating,)): return float(o)
                if isinstance(o, np.ndarray): return o.tolist()
                return super().default(o)
        return json.dumps(val if val is not None else default, cls=_Enc)

    total_value = summary.get("total_value")
    if isinstance(total_value, (np.integer, np.floating)):
        total_value = float(total_value)

    with engine.begin() as conn:
        conn.execute(sql, {
            "portfolio_name":       portfolio_name,
            "zoho_client_id":       zoho_client_id,
            "source_file":          source_file,
            "as_of_date":           as_of_date,
            "total_value":          total_value,
            "asset_allocation":     _json(summary.get("asset_allocation"), {}),
            "sector_concentration": _json(summary.get("sector_concentration"), {}),
            "geographic_exposure":  _json(summary.get("geographic_exposure"), {}),
            "top_10_holdings":      _json(summary.get("top_10_holdings"), []),
            "risk_metrics":         _json(summary.get("risk_metrics"), {}),
        })


def ingest_portfolio(
    df: pd.DataFrame,
    client_id: str,
    as_of_date: Optional[date] = None,
    custodian: Optional[str] = None,
) -> int:
    """
    Upsert all individual holdings rows into the holdings table.

    Args:
        df:         Full holdings DataFrame from AIPortfolioParser.
        client_id:  portfolio_name used as the stable client identifier.
        as_of_date: Statement date. Defaults to today.
        custodian:  Derived from the source PDF filename.

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
