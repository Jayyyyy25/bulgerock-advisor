"""
Tool: market_impact_analyzer
Cross-references a market event with portfolio holdings to identify high-exposure clients.
Supports filtering by asset class and/or specific tickers.
"""
import json
from sqlalchemy import text
from ingestion.db_client import engine


def market_impact_analyzer(
    event_description: str,
    affected_asset_classes: list = None,
    affected_tickers: list = None,
    exposure_threshold_pct: float = 10.0,
) -> str:
    if not affected_asset_classes and not affected_tickers:
        return json.dumps({
            "error": "Provide at least one of: affected_asset_classes or affected_tickers",
            "event": event_description,
        })

    # Build dynamic WHERE clause for affected positions
    exposure_conditions = ["1=0"]  # base case: no match
    params: dict = {"threshold": exposure_threshold_pct}

    if affected_tickers:
        exposure_conditions.append("h.ticker = ANY(:tickers)")
        params["tickers"] = list(affected_tickers)

    if affected_asset_classes:
        exposure_conditions.append("h.asset_class = ANY(:asset_classes)")
        params["asset_classes"] = list(affected_asset_classes)

    exposure_filter = " OR ".join(exposure_conditions)

    sql = f"""
        WITH latest_holdings AS (
            -- For each client, take only the most recent snapshot
            SELECT h.*
            FROM holdings h
            INNER JOIN (
                SELECT client_id, MAX(as_of_date) AS latest_date
                FROM holdings
                GROUP BY client_id
            ) latest ON h.client_id = latest.client_id AND h.as_of_date = latest.latest_date
        ),
        client_totals AS (
            SELECT client_id, SUM(market_value) AS total_aum
            FROM latest_holdings
            GROUP BY client_id
        ),
        affected_exposure AS (
            SELECT
                h.client_id,
                SUM(h.market_value)                         AS exposed_value,
                STRING_AGG(DISTINCT h.asset_class, ', ')    AS exposed_asset_classes,
                STRING_AGG(DISTINCT h.ticker, ', ')         AS exposed_tickers
            FROM latest_holdings h
            WHERE {exposure_filter}
            GROUP BY h.client_id
        )
        SELECT
            c.client_id,
            c.full_name,
            c.risk_profile,
            ae.exposed_value,
            ct.total_aum,
            ROUND(100.0 * ae.exposed_value / NULLIF(ct.total_aum, 0), 2) AS exposure_pct,
            ae.exposed_asset_classes,
            ae.exposed_tickers
        FROM affected_exposure ae
        JOIN client_totals ct  ON ct.client_id = ae.client_id
        JOIN clients c         ON c.client_id  = ae.client_id
        WHERE ROUND(100.0 * ae.exposed_value / NULLIF(ct.total_aum, 0), 2) >= :threshold
        ORDER BY exposure_pct DESC
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return json.dumps({
        "event": event_description,
        "affected_asset_classes": affected_asset_classes or [],
        "affected_tickers": affected_tickers or [],
        "exposure_threshold_pct": exposure_threshold_pct,
        "clients_at_risk": len(rows),
        "affected_clients": [dict(r) for r in rows],
    }, default=str)
