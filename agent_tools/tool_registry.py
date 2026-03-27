"""
Claude tool definitions.

DATA SOURCES:
  - Zoho CRM        → client profiles (name, risk profile, AUM, investment objectives, last meeting date)
  - PostgreSQL       → holdings (raw positions), portfolio_snapshots (derived analytics), policies (insurance)

TOOL SELECTION GUIDE:
  "Tell me about / overview of [client]"  → get_client_full_profile
  "Portfolio / allocation / holdings"     → query_clients (name→ID) then query_portfolio
  "Policies / insurance / coverage"       → query_clients (name→ID) then query_policies  (or query_policies() for all)
  "List all clients"                      → query_clients (no args)
  "All policies"                          → query_policies (no args)
  "Who is exposed to [market event]"      → market_impact_analyzer
"""

TOOLS = [
    {
        "name": "get_client_full_profile",
        "description": (
            "Fetch everything about a single client in one call: "
            "CRM profile (name, risk, AUM, objectives, last meeting date) from Zoho, "
            "full portfolio data (asset allocation, sector/geo breakdown, top 10 holdings, risk metrics) from PostgreSQL, "
            "and all insurance policies from PostgreSQL. "
            "Use this for general questions like 'tell me about [client]', 'give me a summary of [client]', "
            "or any request where multiple data types are needed for one client."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Client ID in CLI format (e.g. 'CLI001'). Call query_clients first if you only have a name.",
                },
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "query_clients",
        "description": (
            "Fetch client profiles from Zoho CRM. "
            "No arguments → returns ALL clients. "
            "name_contains='East' → searches by name (use last word of company name, e.g. 'Asia', 'Trust', 'Capital'). "
            "Returns client_id (CLI001–CLI007), full_name, risk_profile, AUM, investment_objectives, last_meeting_date. "
            "Use to resolve a client name to a client_id, or to list/filter all clients."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name_contains": {
                    "type": "string",
                    "description": "Partial last word of client name to search (e.g. 'Asia', 'Trust', 'Alpine', 'Capital', 'Bridge', 'Office', 'Custodian')",
                },
                "risk_profile": {
                    "type": "string",
                    "enum": ["conservative", "moderate", "aggressive"],
                    "description": "Filter by risk profile",
                },
                "min_aum": {"type": "number", "description": "Minimum AUM in USD"},
                "max_aum": {"type": "number", "description": "Maximum AUM in USD"},
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
        },
    },
    {
        "name": "query_portfolio",
        "description": (
            "Fetch portfolio data for one client from PostgreSQL. "
            "Returns: asset allocation (%), sector concentration (%), geographic exposure (%), "
            "top 10 holdings by market value, risk metrics, total AUM, as_of_date. "
            "Use for focused portfolio/allocation/holdings questions about a single client. "
            "Requires client_id (CLI format). If you only have a name, call query_clients first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "CLI format client ID (e.g. 'CLI001')",
                },
                "as_of_date": {
                    "type": "string",
                    "description": "Date YYYY-MM-DD. Defaults to most recent snapshot.",
                },
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "query_policies",
        "description": (
            "Fetch insurance policies from PostgreSQL. "
            "No arguments → ALL policies for ALL clients. "
            "client_id='CLI006' → policies for that one client only. "
            "days_ahead=30 → only policies renewing within 30 days. "
            "Returns: policy_id, client_id, client full_name, policy_type, insurer, coverage_amount, premium, renewal_date, coverage_type. "
            "Use for any question about insurance, coverage, premiums, or renewals."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Optional CLI client ID to filter to one client",
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "Optional: only return policies renewing within this many days",
                },
            },
        },
    },
    {
        "name": "query_unmet_clients",
        "description": (
            "Find clients who have not been met recently, based on Last_Meeting date in Zoho CRM. "
            "Use for questions like 'which clients haven't been met in 30 days', 'who needs a follow-up', "
            "'clients not seen in 2 weeks', or any client engagement / meeting cadence check. "
            "Returns each client's name, risk profile, AUM, last meeting date, and days since last meeting."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Threshold in days. Clients not met within this period are returned. Default 30. Use 14 for 2-week check.",
                },
            },
        },
    },
    {
        "name": "scan_market_impact",
        "description": (
            "Scan ALL client portfolios against a market event described in plain English "
            "(e.g. 'US-China trade war', 'Fed rate spike', 'oil price crash', 'tech sector selloff'). "
            "Claude analyses each portfolio individually using asset allocation, sector concentration, "
            "geographic exposure and top holdings, then ranks all clients by impact severity. "
            "Returns per-client: severity (Critical/High/Moderate/Low/Minimal), estimated portfolio loss %, "
            "vulnerable and resilient holdings, rebalancing actions with trade sizes, "
            "recommended actions the RM should take, and an executive summary. "
            "Use this whenever an investment manager asks about market events, scenarios, or which clients are affected."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_description": {
                    "type": "string",
                    "description": "Natural language description of the market event, e.g. 'Russia-Ukraine war escalation' or '100bps Fed rate hike'",
                },
            },
            "required": ["event_description"],
        },
    },
    {
        "name": "market_impact_analyzer",
        "description": (
            "Analyze which clients are most exposed to a market event "
            "(e.g. 'Fed rate hike', 'China tech crackdown', 'oil spike'). "
            "Cross-references all client holdings in PostgreSQL against affected asset classes or tickers. "
            "Returns each affected client's exposure %, exposed value, AUM, and risk profile. "
            "Use for 'who is exposed to X', risk alerts, or proactive RM outreach questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_description": {
                    "type": "string",
                    "description": "Description of the market event",
                },
                "affected_asset_classes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Asset classes impacted (e.g. ['Fixed Income', 'Equities'])",
                },
                "affected_tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific tickers impacted",
                },
                "exposure_threshold_pct": {
                    "type": "number",
                    "description": "Minimum exposure % to flag a client (default 10.0)",
                },
            },
            "required": ["event_description"],
        },
    },
]
