"""
Tool: query_portfolio
Returns asset class allocation breakdown and top 5 holdings for a client.
Defaults to the most recent as_of_date available for that client.
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

    top5_sql = f"""
        SELECT
            ticker,
            security_name,
            isin,
            asset_class,
            sector,
            account_type,
            quantity,
            market_value
        FROM holdings h
        WHERE h.client_id = :client_id
          AND {date_filter}
        ORDER BY market_value DESC
        LIMIT 5
    """

    total_aum_sql = f"""
        SELECT SUM(market_value) AS total_aum, MAX(as_of_date) AS as_of_date
        FROM holdings h
        WHERE h.client_id = :client_id
          AND {date_filter}
    """

    with engine.connect() as conn:
        allocation = conn.execute(text(allocation_sql), params).mappings().all()
        top5 = conn.execute(text(top5_sql), params).mappings().all()
        summary = conn.execute(text(total_aum_sql), params).mappings().first()

    if not allocation:
        return json.dumps({"error": f"No holdings found for client {client_id}"})

    return json.dumps({
        "client_id": client_id,
        "as_of_date": str(summary["as_of_date"]) if summary else None,
        "total_aum_usd": float(summary["total_aum"]) if summary and summary["total_aum"] else 0,
        "allocation": [dict(r) for r in allocation],
        "top_5_holdings": [dict(r) for r in top5],
    }, default=str)
