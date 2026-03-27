"""
Market event impact analysis using Claude.
"""
import json
import os
import re

from anthropic import Anthropic

_CREDENTIALS_PATH = os.path.expanduser("~/.claude/.credentials.json")


def _get_api_key() -> str:
    try:
        with open(_CREDENTIALS_PATH) as f:
            creds = json.load(f)
        token = creds.get("claudeAiOauth", {}).get("accessToken", "")
        if token:
            return token
    except Exception:
        pass
    return os.environ["ANTHROPIC_API_KEY"]


class MarketImpactAnalyzer:
    def __init__(self):
        self.client = Anthropic(api_key=_get_api_key())

    def assess_impact(self, client_json_data: dict, market_event: str) -> dict:
        total_value         = client_json_data.get("total_value", 0)
        asset_allocation    = client_json_data.get("asset_allocation", {})
        sector_concentration = client_json_data.get("sector_concentration", {})
        geographic_exposure = client_json_data.get("geographic_exposure", {})
        top_holdings        = client_json_data.get("top_10_holdings", [])

        portfolio_context = f"""Total Value: ${total_value:,.2f}
Asset Allocation (%): {json.dumps(asset_allocation)}
Sector Concentration (%): {json.dumps(sector_concentration)}
Geographic Exposure (%): {json.dumps(geographic_exposure)}
Top Holdings: {json.dumps(top_holdings[:10])}"""

        prompt = f"""You are a senior portfolio risk analyst at a wealth management firm.
Analyse the impact of the following market event on the client portfolio.

MARKET EVENT: {market_event}

{portfolio_context}

Respond with ONLY a valid JSON object — no preamble, no markdown:
{{
    "portfolio_impact_score": <integer -10 to 10>,
    "impact_severity": "<Critical | High | Moderate | Low | Minimal>",
    "estimated_portfolio_loss_pct": <number, negative = loss, e.g. -8.5>,
    "asset_class_impacts": [
        {{
            "asset_class": "<name matching keys in Asset Allocation above>",
            "estimated_change_pct": <number, negative = loss, e.g. -15.0>
        }}
    ],
    "rebalancing_actions": [
        {{
            "action": "<BUY | REDUCE | HOLD>",
            "asset_class": "<name>",
            "from_pct": <current allocation % as number>,
            "to_pct": <recommended target allocation % as number>,
            "rationale": "<one short sentence>"
        }}
    ],
    "vulnerable_holdings": [{{"security_name": "", "reason": "", "estimated_impact": "<High|Medium|Low>"}}],
    "resilient_holdings":  [{{"security_name": "", "reason": "", "estimated_impact": "<Positive|Neutral>"}}],
    "executive_summary": "<2-3 sentences an RM can share with the client>",
    "recommended_actions": ["<action 1>", "<action 2>", "<action 3>"]
}}

Only include asset classes that are actually present in the portfolio. For rebalancing_actions, only include BUY or REDUCE (omit HOLD entries).
DISCLAIMER: AI-assisted assessment only, not financial advice."""

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            raw   = response.content[0].text.strip()
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError("No JSON found in Claude response")

            result = json.loads(match.group(0))
            result.setdefault("portfolio_impact_score", 0)
            result.setdefault("impact_severity", "Unknown")
            result.setdefault("estimated_portfolio_loss_pct", 0)
            result.setdefault("asset_class_impacts", [])
            result.setdefault("rebalancing_actions", [])
            result.setdefault("vulnerable_holdings", [])
            result.setdefault("resilient_holdings", [])
            result.setdefault("executive_summary", "Analysis unavailable.")
            result.setdefault("recommended_actions", [])

            # Enrich asset_class_impacts with dollar values computed from known portfolio data
            for item in result["asset_class_impacts"]:
                ac = item.get("asset_class", "")
                current_pct = float(asset_allocation.get(ac, 0))
                current_value = total_value * current_pct / 100
                change_pct = float(item.get("estimated_change_pct", 0))
                item["current_pct"] = current_pct
                item["current_value"] = current_value
                item["estimated_change_value"] = current_value * change_pct / 100

            # Enrich rebalancing_actions with trade dollar size
            for action in result["rebalancing_actions"]:
                from_pct = float(action.get("from_pct", 0))
                to_pct = float(action.get("to_pct", 0))
                action["trade_value"] = abs(to_pct - from_pct) * total_value / 100

            return result

        except Exception as e:
            return {
                "portfolio_impact_score": 0,
                "impact_severity": "Unknown",
                "vulnerable_holdings": [],
                "resilient_holdings": [],
                "executive_summary": f"Analysis could not be completed: {e}",
                "recommended_actions": [],
                "error": str(e),
            }
