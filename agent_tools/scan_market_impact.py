"""
Tool: scan_market_impact
Scans ALL client portfolios against a natural-language market event description.
Uses Claude to assess impact on each portfolio individually, then ranks results by severity.
No need to specify asset classes — Claude infers them from the event.
"""
import json
from sqlalchemy import text
from ingestion.db_client import engine
from portfolio.impact_analysis import MarketImpactAnalyzer
from agent_tools.zoho_client import get_contacts_by_client_ids

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3, "Minimal": 4, "Unknown": 5}


def scan_market_impact(event_description: str) -> str:
    """
    Analyse the impact of a market event across all client portfolios.

    Args:
        event_description: Natural language description of the event,
                           e.g. "US-China trade war escalation" or "Fed rate spike of 100bps".

    Returns:
        JSON with per-client impact ranked by severity, plus an overall summary.
    """
    # 1. Fetch all latest portfolio snapshots from DB
    sql = text("""
        SELECT DISTINCT ON (portfolio_name)
            portfolio_name,
            zoho_client_id,
            total_value,
            asset_allocation,
            sector_concentration,
            geographic_exposure,
            top_10_holdings
        FROM portfolio_snapshots
        ORDER BY portfolio_name, as_of_date DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    if not rows:
        return json.dumps({"error": "No portfolio data found in database."})

    # 2. Enrich with client names from Zoho CRM
    client_ids = [r["zoho_client_id"] for r in rows if r["zoho_client_id"]]
    clients_by_id = get_contacts_by_client_ids(client_ids)

    # 3. Run Claude impact analysis on each portfolio
    analyzer = MarketImpactAnalyzer()
    results = []

    for row in rows:
        client_id   = row["zoho_client_id"] or row["portfolio_name"]
        client_info = clients_by_id.get(client_id, {})
        full_name   = client_info.get("full_name") or row["portfolio_name"]
        risk_profile = client_info.get("risk_profile", "unknown")
        total_value = float(row["total_value"] or 0)

        portfolio_data = {
            "total_value":          total_value,
            "asset_allocation":     row["asset_allocation"] or {},
            "sector_concentration": row["sector_concentration"] or {},
            "geographic_exposure":  row["geographic_exposure"] or {},
            "top_10_holdings":      row["top_10_holdings"] or [],
        }

        impact = analyzer.assess_impact(portfolio_data, event_description)

        results.append({
            "client_id":                  client_id,
            "client_name":                full_name,
            "risk_profile":               risk_profile,
            "total_aum":                  total_value,
            "impact_severity":            impact.get("impact_severity", "Unknown"),
            "portfolio_impact_score":     impact.get("portfolio_impact_score", 0),
            "estimated_portfolio_loss_pct": impact.get("estimated_portfolio_loss_pct", 0),
            "estimated_loss_value":       total_value * abs(impact.get("estimated_portfolio_loss_pct", 0)) / 100,
            "asset_class_impacts":        impact.get("asset_class_impacts", []),
            "rebalancing_actions":        impact.get("rebalancing_actions", []),
            "vulnerable_holdings":        impact.get("vulnerable_holdings", [])[:3],
            "resilient_holdings":         impact.get("resilient_holdings", [])[:2],
            "executive_summary":          impact.get("executive_summary", ""),
            "recommended_actions":        impact.get("recommended_actions", []),
        })

    # 4. Rank by severity then impact score
    results.sort(key=lambda r: (
        SEVERITY_ORDER.get(r["impact_severity"], 5),
        r["portfolio_impact_score"],
    ))

    # 5. Overall summary stats
    severity_counts = {}
    for r in results:
        severity_counts[r["impact_severity"]] = severity_counts.get(r["impact_severity"], 0) + 1

    total_estimated_loss = sum(r["estimated_loss_value"] for r in results)

    return json.dumps({
        "event":                  event_description,
        "portfolios_scanned":     len(results),
        "severity_breakdown":     severity_counts,
        "total_estimated_loss":   total_estimated_loss,
        "clients_ranked":         results,
    }, default=str)
