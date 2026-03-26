"""
Portfolio analysis endpoints: stress testing and cross-portfolio screening.
All portfolio data is read from PostgreSQL — no JSON files.
"""
import json
import os
from typing import List, Optional

import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from ingestion.db_client import engine
from portfolio.impact_analysis import MarketImpactAnalyzer

router = APIRouter()

_impact_analyzer: Optional[MarketImpactAnalyzer] = None


def get_impact_analyzer() -> MarketImpactAnalyzer:
    global _impact_analyzer
    if _impact_analyzer is None:
        _impact_analyzer = MarketImpactAnalyzer()
    return _impact_analyzer


class StressTestRequest(BaseModel):
    client_id:   str    # portfolio_name
    market_event: str


class CrossPortfolioRequest(BaseModel):
    dimension: str          # "asset_class" | "sector" | "geography"
    threshold: float
    operator:  str = ">"
    category:  Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class CrossPortfolioChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


def _load_latest_snapshot(portfolio_name: str) -> dict:
    """Fetch the most recent snapshot for a portfolio from the DB."""
    sql = text("""
        SELECT portfolio_name, zoho_client_id, source_file, as_of_date,
               total_value, asset_allocation, sector_concentration,
               geographic_exposure, top_10_holdings, risk_metrics
        FROM portfolio_snapshots
        WHERE portfolio_name = :portfolio_name
        ORDER BY as_of_date DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"portfolio_name": portfolio_name}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Portfolio '{portfolio_name}' not found.")

    return {
        "client_id":           row["portfolio_name"],
        "zoho_client_id":      row["zoho_client_id"],
        "source_file":         row["source_file"],
        "as_of_date":          str(row["as_of_date"]),
        "total_value":         float(row["total_value"] or 0),
        "asset_allocation":    row["asset_allocation"] or {},
        "sector_concentration": row["sector_concentration"] or {},
        "geographic_exposure": row["geographic_exposure"] or {},
        "top_10_holdings":     row["top_10_holdings"] or [],
        "risk_metrics":        row["risk_metrics"] or {},
    }


@router.get("/portfolios")
def list_portfolios():
    """List all portfolios — latest snapshot per portfolio_name."""
    sql = text("""
        SELECT DISTINCT ON (portfolio_name)
            portfolio_name, zoho_client_id, source_file, as_of_date,
            total_value, asset_allocation, risk_metrics
        FROM portfolio_snapshots
        ORDER BY portfolio_name, as_of_date DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    portfolios = [
        {
            "client_id":        row["portfolio_name"],
            "zoho_client_id":   row["zoho_client_id"],
            "source_file":      row["source_file"],
            "as_of_date":       str(row["as_of_date"]),
            "total_value":      float(row["total_value"] or 0),
            "asset_allocation": row["asset_allocation"] or {},
            "risk_metrics":     row["risk_metrics"] or {},
        }
        for row in rows
    ]
    return {"portfolios": portfolios, "count": len(portfolios)}


@router.get("/portfolios/{portfolio_name}/history")
def portfolio_history(portfolio_name: str):
    """List all snapshots (all periods) for a given portfolio."""
    sql = text("""
        SELECT as_of_date, total_value, source_file, ingested_at
        FROM portfolio_snapshots
        WHERE portfolio_name = :portfolio_name
        ORDER BY as_of_date DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"portfolio_name": portfolio_name}).mappings().all()

    return {
        "portfolio_name": portfolio_name,
        "snapshots": [
            {
                "as_of_date":   str(r["as_of_date"]),
                "total_value":  float(r["total_value"] or 0),
                "source_file":  r["source_file"],
                "ingested_at":  str(r["ingested_at"]),
            }
            for r in rows
        ],
    }


@router.get("/portfolios/{portfolio_name}")
def get_portfolio(portfolio_name: str):
    """Return the latest snapshot for a portfolio."""
    return _load_latest_snapshot(portfolio_name)


@router.post("/stress-test")
def stress_test(request: StressTestRequest):
    """Run a Claude-powered market event stress test on a portfolio."""
    client_data = _load_latest_snapshot(request.client_id)
    result = get_impact_analyzer().assess_impact(client_data, request.market_event)
    return {"client_id": request.client_id, "market_event": request.market_event, "analysis": result}


@router.post("/cross-portfolio")
def cross_portfolio(request: CrossPortfolioRequest):
    """Screen all portfolios by exposure dimension — pure SQL + pandas, no AI."""
    valid_dimensions = {"asset_class", "sector", "geography"}
    valid_operators  = {">", "<", ">=", "<=", "=="}

    if request.dimension not in valid_dimensions:
        raise HTTPException(status_code=400, detail=f"dimension must be one of {sorted(valid_dimensions)}")
    if request.operator not in valid_operators:
        raise HTTPException(status_code=400, detail=f"operator must be one of {sorted(valid_operators)}")

    # Load latest snapshot per portfolio
    sql = text("""
        SELECT DISTINCT ON (portfolio_name)
            portfolio_name, total_value, asset_allocation, sector_concentration, geographic_exposure
        FROM portfolio_snapshots
        ORDER BY portfolio_name, as_of_date DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    dim_map = {
        "asset_class": "asset_allocation",
        "sector":      "sector_concentration",
        "geography":   "geographic_exposure",
    }
    field = dim_map[request.dimension]
    ops = {">": lambda a, b: a > b, "<": lambda a, b: a < b,
           ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
           "==": lambda a, b: a == b}
    op_fn = ops[request.operator]

    results = []
    for row in rows:
        data = row[field] or {}
        matches = []
        for category, pct in data.items():
            if request.category and category.upper() != request.category.upper():
                continue
            if op_fn(float(pct), request.threshold):
                matches.append({"category": category, "percentage": float(pct)})

        if matches:
            matches.sort(key=lambda x: x["percentage"], reverse=True)
            results.append({
                "client_id":   row["portfolio_name"],
                "total_value": float(row["total_value"] or 0),
                "matches":     matches,
            })

    results.sort(key=lambda x: max(m["percentage"] for m in x["matches"]), reverse=True)
    return {"query": request.model_dump(), "results": results, "count": len(results)}


def _execute_screen_portfolios(params: dict) -> dict:
    """Query holdings table for cross-portfolio exposure screening."""
    asset_class = params.get("asset_class")
    sector = params.get("sector")
    geography = params.get("geography")
    min_pct = params.get("min_pct", 0) or 0
    max_pct = params.get("max_pct", 100) or 100

    conditions = ["h.as_of_date = latest.max_date"]
    bind_params: dict = {"min_pct": min_pct, "max_pct": max_pct}

    if asset_class:
        conditions.append("UPPER(h.asset_class) LIKE UPPER(:asset_class)")
        bind_params["asset_class"] = f"%{asset_class}%"
    if sector:
        conditions.append("UPPER(h.sector) LIKE UPPER(:sector)")
        bind_params["sector"] = f"%{sector}%"
    if geography:
        conditions.append("UPPER(h.geography) LIKE UPPER(:geography)")
        bind_params["geography"] = f"%{geography}%"

    where_clause = " AND ".join(conditions)

    sql = text(f"""
        WITH latest AS (
            SELECT client_id, MAX(as_of_date) AS max_date
            FROM holdings
            GROUP BY client_id
        ),
        portfolio_totals AS (
            SELECT h.client_id, SUM(h.market_value) AS total_value
            FROM holdings h
            JOIN latest ON h.client_id = latest.client_id AND h.as_of_date = latest.max_date
            GROUP BY h.client_id
        ),
        filtered AS (
            SELECT h.client_id, SUM(h.market_value) AS exposure_value
            FROM holdings h
            JOIN latest ON h.client_id = latest.client_id
            WHERE {where_clause}
            GROUP BY h.client_id
        )
        SELECT
            f.client_id,
            f.exposure_value,
            pt.total_value,
            ROUND((f.exposure_value * 100.0 / pt.total_value)::numeric, 2) AS exposure_pct
        FROM filtered f
        JOIN portfolio_totals pt ON f.client_id = pt.client_id
        WHERE (f.exposure_value * 100.0 / pt.total_value) BETWEEN :min_pct AND :max_pct
        ORDER BY exposure_pct DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, bind_params).mappings().all()

    results = [
        {
            "client_id": row["client_id"],
            "exposure_value": float(row["exposure_value"]),
            "total_value": float(row["total_value"]),
            "exposure_pct": float(row["exposure_pct"]),
        }
        for row in rows
    ]

    # Add per-asset-class breakdown within the filtered holdings
    if results:
        breakdown_sql = text(f"""
            WITH latest AS (
                SELECT client_id, MAX(as_of_date) AS max_date
                FROM holdings
                GROUP BY client_id
            ),
            portfolio_totals AS (
                SELECT h.client_id, SUM(h.market_value) AS total_value
                FROM holdings h
                JOIN latest ON h.client_id = latest.client_id AND h.as_of_date = latest.max_date
                GROUP BY h.client_id
            ),
            breakdown AS (
                SELECT h.client_id, h.asset_class AS category, SUM(h.market_value) AS cat_value
                FROM holdings h
                JOIN latest ON h.client_id = latest.client_id
                WHERE {where_clause}
                GROUP BY h.client_id, h.asset_class
            )
            SELECT
                b.client_id,
                b.category,
                ROUND((b.cat_value * 100.0 / pt.total_value)::numeric, 2) AS pct
            FROM breakdown b
            JOIN portfolio_totals pt ON b.client_id = pt.client_id
            ORDER BY b.client_id, pct DESC
        """)

        matched_ids = {r["client_id"] for r in results}
        with engine.connect() as conn:
            brows = conn.execute(breakdown_sql, bind_params).mappings().all()

        breakdown_map: dict = {}
        for brow in brows:
            cid = brow["client_id"]
            if cid in matched_ids:
                breakdown_map.setdefault(cid, []).append({
                    "category": brow["category"] or "Other",
                    "percentage": float(brow["pct"]),
                })

        for r in results:
            r["matched_categories"] = breakdown_map.get(r["client_id"], [])

    return {
        "filters_applied": params,
        "matched_clients": len(results),
        "results": results,
    }


def _execute_breakdown_screen(params: dict) -> dict:
    """Query portfolio_snapshots JSONB for per-category breakdown screening."""
    dimension = params.get("dimension")
    min_pct = float(params.get("min_pct", 0) or 0)
    max_pct = float(params.get("max_pct", 100) or 100)

    dim_map = {
        "asset_class": "asset_allocation",
        "sector": "sector_concentration",
        "geography": "geographic_exposure",
    }

    if dimension not in dim_map:
        return {"error": f"dimension must be one of {list(dim_map.keys())}"}

    field = dim_map[dimension]

    sql = text(f"""
        SELECT DISTINCT ON (portfolio_name)
            portfolio_name, total_value, {field}
        FROM portfolio_snapshots
        ORDER BY portfolio_name, as_of_date DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    results = []
    for row in rows:
        data = row[field] or {}
        matched = [
            {"category": cat, "percentage": float(pct)}
            for cat, pct in data.items()
            if min_pct <= float(pct) <= max_pct
        ]
        if matched:
            matched.sort(key=lambda x: x["percentage"], reverse=True)
            total_matched_pct = sum(cat["percentage"] for cat in matched)
            total = float(row["total_value"] or 0)
            results.append({
                "client_id": row["portfolio_name"],
                "total_value": total,
                "exposure_pct": total_matched_pct,
                "exposure_value": total * total_matched_pct / 100,
                "matched_categories": matched,
            })

    results.sort(key=lambda x: x["exposure_pct"], reverse=True)
    return {
        "filters_applied": params,
        "matched_clients": len(results),
        "results": results,
    }


_CHAT_SYSTEM_PROMPT = """You are a cross-portfolio screening assistant for BugleRock Advisors.
You help relationship managers identify client exposure patterns across all portfolios.

You have two tools:
- screen_portfolios: use when the user names a specific category, e.g. "China", "Equities", "Technology". Queries raw holdings and supports compound filters.
- screen_by_dimension: use when the user asks about any or all categories in a dimension, e.g. "any asset class above 20%", "sector breakdown", "show Fixed Income allocation". Returns all matching categories per client.

Write your response as plain conversational prose only — no markdown tables, no bullet lists, no bold or italic formatting, no headers.
Just 2-4 sentences of narrative insight: which clients matched, what the exposure levels suggest, and any notable pattern.
The UI will display the structured data visually — you only need to provide the written interpretation.
If no clients match, say so in one sentence and suggest a broader query.
Always frame your analysis as AI-assisted assessment, not financial advice."""

_SCREEN_TOOL = {
    "name": "screen_portfolios",
    "description": (
        "Screen all client portfolios by exposure. Returns clients whose holdings match "
        "the specified asset class, sector, and/or geography, along with their allocation percentages."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "asset_class": {
                "type": "string",
                "description": "Filter by asset class, e.g. 'Equities', 'Fixed Income', 'Cash', 'Alternatives'. Case-insensitive partial match.",
            },
            "sector": {
                "type": "string",
                "description": "Filter by sector, e.g. 'Technology', 'Healthcare', 'Financial Services'. Case-insensitive partial match.",
            },
            "geography": {
                "type": "string",
                "description": "Filter by geography/country, e.g. 'China', 'United States', 'Europe', 'Singapore'. Case-insensitive partial match.",
            },
            "min_pct": {
                "type": "number",
                "description": "Minimum allocation percentage (0–100). Only return clients with exposure at or above this level.",
            },
            "max_pct": {
                "type": "number",
                "description": "Maximum allocation percentage (0–100). Only return clients with exposure at or below this level.",
            },
        },
        "required": [],
    },
}


_BREAKDOWN_TOOL = {
    "name": "screen_by_dimension",
    "description": (
        "Screen all client portfolios by dimension to find clients where ANY category "
        "in that dimension meets the percentage threshold. Use this for queries like "
        "'clients with any asset class above 20%', 'show sector breakdown', or "
        "'which clients have significant Fixed Income'. Returns all matching categories per client."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "dimension": {
                "type": "string",
                "enum": ["asset_class", "sector", "geography"],
                "description": "Dimension to screen: 'asset_class', 'sector', or 'geography'.",
            },
            "min_pct": {
                "type": "number",
                "description": "Minimum allocation percentage (0-100). Defaults to 0.",
            },
            "max_pct": {
                "type": "number",
                "description": "Maximum allocation percentage (0-100). Defaults to 100.",
            },
        },
        "required": ["dimension"],
    },
}


@router.post("/cross-portfolio-chat")
def cross_portfolio_chat(request: CrossPortfolioChatRequest):
    """Natural language cross-portfolio screening powered by Claude."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    messages = [{"role": m.role, "content": m.content} for m in request.history]
    messages.append({"role": "user", "content": request.message})

    tools = [_SCREEN_TOOL, _BREAKDOWN_TOOL]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=_CHAT_SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    )

    tool_results_data = None

    if response.stop_reason == "tool_use":
        tool_use_block = next(b for b in response.content if b.type == "tool_use")

        if tool_use_block.name == "screen_portfolios":
            tool_results_data = _execute_screen_portfolios(tool_use_block.input)
        elif tool_use_block.name == "screen_by_dimension":
            tool_results_data = _execute_breakdown_screen(tool_use_block.input)

        # Serialize SDK content blocks to plain dicts before passing back
        serialized_content = []
        for block in response.content:
            if block.type == "text":
                serialized_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                serialized_content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})

        messages.append({"role": "assistant", "content": serialized_content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": json.dumps(tool_results_data),
            }],
        })

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_CHAT_SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

    text_response = next((b.text for b in response.content if hasattr(b, "text")), "")
    return {"response": text_response, "results": tool_results_data}
