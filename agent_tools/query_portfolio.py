"""
Tool: query_portfolio
Returns full portfolio data for a client: asset allocation, sector concentration,
geographic exposure, risk metrics, and top holdings.
Pulls from both holdings (raw) and portfolio_snapshots (derived analytics).
"""
import json
from sqlalchemy import text
from ingestion.db_client import engine


def query_portfolio(client_id: str, as_of_date: str = None) -> str:
    if as_of_date:
        date_filter = "h.as_of_date = :as_of_date"
        params = {"client_id": client_id, "as_of_date": as_of_date}
    else:
        date_filter = """
            h.as_of_date = (
                SELECT MAX(as_of_date) FROM holdings WHERE client_id = :client_id
            )
        """
        params = {"client_id": client_id}

    allocation_sql = f"""
        SELECT
            asset_class,
            SUM(market_value)                                                    AS total_value,
            ROUND(
                100.0 * SUM(market_value) / NULLIF(SUM(SUM(market_value)) OVER (), 0),
                2
            )                                                                    AS pct
        FROM holdings h
        WHERE h.client_id = :client_id
          AND {date_filter}
        GROUP BY asset_class
        ORDER BY total_value DESC
    """

    top10_sql = f"""
        SELECT
            security_name,
            asset_class,
            sector,
            geography,
            market_value
        FROM holdings h
        WHERE h.client_id = :client_id
          AND {date_filter}
          AND market_value > 0
        ORDER BY market_value DESC
        LIMIT 10
    """

    summary_sql = f"""
        SELECT SUM(market_value) AS total_aum, MAX(as_of_date) AS as_of_date
        FROM holdings h
        WHERE h.client_id = :client_id
          AND {date_filter}
    """

    # Pull sector/geography/risk from portfolio_snapshots
    snapshot_sql = """
        SELECT sector_concentration, geographic_exposure, risk_metrics
        FROM portfolio_snapshots
        WHERE zoho_client_id = :client_id
        ORDER BY as_of_date DESC
        LIMIT 1
    """

    with engine.connect() as conn:
        allocation = conn.execute(text(allocation_sql), params).mappings().all()
        top10 = conn.execute(text(top10_sql), params).mappings().all()
        summary = conn.execute(text(summary_sql), params).mappings().first()
        snapshot = conn.execute(text(snapshot_sql), {"client_id": client_id}).mappings().first()

    if not allocation:
        return json.dumps({"error": f"No portfolio data found for client {client_id}"})

    result = {
        "client_id": client_id,
        "as_of_date": str(summary["as_of_date"]) if summary else None,
        "total_aum_usd": float(summary["total_aum"]) if summary and summary["total_aum"] else 0,
        "asset_allocation": [dict(r) for r in allocation],
        "top_10_holdings": [dict(r) for r in top10],
        "sector_concentration": snapshot["sector_concentration"] if snapshot else {},
        "geographic_exposure": snapshot["geographic_exposure"] if snapshot else {},
        "risk_metrics": snapshot["risk_metrics"] if snapshot else {},
    }
    return json.dumps(result, default=str)
