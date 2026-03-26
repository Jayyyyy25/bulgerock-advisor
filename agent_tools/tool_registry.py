"""
Claude tool definitions.
These schemas must exactly match the function signatures in the corresponding tool files.
The tool_dispatcher maps these names to Python callables.
"""

TOOLS = [
    {
        "name": "query_clients",
        "description": (
            "Search for wealth management clients by name, advisor, risk profile, or AUM range. "
            "Returns client profile data including contact info, risk level, and total AUM. "
            "Use this when the RM asks about specific clients or wants to filter the client book."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name_contains": {
                    "type": "string",
                    "description": "Partial name match (case-insensitive)",
                },
                "advisor_id": {
                    "type": "string",
                    "description": "Filter by advisor ID (e.g., 'ADV01')",
                },
                "risk_profile": {
                    "type": "string",
                    "enum": ["conservative", "moderate", "aggressive"],
                    "description": "Filter by client risk profile",
                },
                "min_aum": {
                    "type": "number",
                    "description": "Minimum AUM in USD",
                },
                "max_aum": {
                    "type": "number",
                    "description": "Maximum AUM in USD",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10)",
                },
            },
        },
    },
    {
        "name": "query_portfolio",
        "description": (
            "Get asset class allocation breakdown and top 5 holdings by market value for a specific client. "
            "Returns allocation percentages (Equity %, Fixed Income %, Cash %, etc.) and individual holding details. "
            "Use this when the RM asks about a client's portfolio composition or investment mix."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "The unique client identifier (e.g., 'CLI001')",
                },
                "as_of_date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format. Defaults to most recent available date.",
                },
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "query_policies",
        "description": (
            "Scan for insurance policies (Life, Disability, Long-Term Care) renewing within a specified number of days. "
            "Can filter to a single client or scan all clients. "
            "Use this for renewal reminders, upcoming policy reviews, or compliance checks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Optional: filter to a single client's policies",
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days to look ahead for renewals (default: 30)",
                },
            },
        },
    },
    {
        "name": "market_impact_analyzer",
        "description": (
            "Analyze which clients are most exposed to a hypothetical market event "
            "(e.g., 'Fed rate hike', 'tech sector selloff', 'oil price spike'). "
            "Provide affected asset classes or tickers; returns clients above an exposure threshold "
            "with their exact exposure percentage. Use for risk alerts and proactive RM outreach."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_description": {
                    "type": "string",
                    "description": "Human-readable description of the market event",
                },
                "affected_asset_classes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Asset classes impacted (e.g., ['Fixed Income', 'Equity'])",
                },
                "affected_tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific tickers impacted (e.g., ['TLT', 'BND'])",
                },
                "exposure_threshold_pct": {
                    "type": "number",
                    "description": "Minimum portfolio exposure % to flag a client (default: 10.0)",
                },
            },
            "required": ["event_description"],
        },
    },
]
