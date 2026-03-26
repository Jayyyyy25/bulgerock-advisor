"""
Post-ingestion AUM recalculation.
Updates the denormalized aum column on clients based on the latest holdings snapshot.
"""
from sqlalchemy import text
from .db_client import engine

AUM_UPDATE_SQL = """
UPDATE clients c
SET
    aum        = sub.total_aum,
    updated_at = NOW()
FROM (
    SELECT
        h.client_id,
        SUM(h.market_value) AS total_aum
    FROM holdings h
    INNER JOIN (
        SELECT client_id, MAX(as_of_date) AS latest_date
        FROM holdings
        GROUP BY client_id
    ) latest ON h.client_id = latest.client_id AND h.as_of_date = latest.latest_date
    GROUP BY h.client_id
) sub
WHERE c.client_id = sub.client_id;
"""


def recalculate_aum() -> int:
    """Recalculate AUM for all clients with holdings. Returns number of clients updated."""
    with engine.begin() as conn:
        result = conn.execute(text(AUM_UPDATE_SQL))
        return result.rowcount
