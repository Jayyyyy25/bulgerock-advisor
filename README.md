# Pocket IA — AI-Powered Wealth Management Assistant

An agentic Slack bot + web dashboard for Relationship Managers (RMs), powered by Claude.

## Architecture

```
pocket-ia/
├── db/               ← PostgreSQL schema + seed data
├── ingestion/        ← CSV parsers + upsert engine (pandas + SQLAlchemy)
├── agent_tools/      ← Claude tool implementations (dynamic SQL)
├── slack_bot/        ← Slack bot (slack-bolt Socket Mode) + scheduler
├── api/              ← FastAPI REST backend
└── dashboard/        ← React + Vite + Tailwind (Client 360 UI)
```

## Setup

### 1. PostgreSQL

```bash
createdb pocketia
createuser pocketia --pwprompt
psql pocketia < db/schema.sql
psql pocketia < db/seed_data/sample_clients.sql
```

### 2. Python environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration

```bash
cp .env.example .env
# Fill in: DATABASE_URL, ANTHROPIC_API_KEY, SLACK_BOT_TOKEN, SLACK_APP_TOKEN
```

### 4. Ingest sample data

```bash
# From the pocket-ia/ directory:
python -m ingestion.run_ingestion --custodian custodian_a --file db/seed_data/custodian_a_sample.csv
python -m ingestion.run_ingestion --custodian custodian_b --file db/seed_data/custodian_b_sample.csv
```

### 5. Start the API

```bash
uvicorn api.main:app --reload --port 8000
# Docs at: http://localhost:8000/docs
```

### 6. Start the Slack bot

```bash
python -m slack_bot.app
```

### 7. Start the React dashboard

```bash
cd dashboard
npm install
npm run dev
# Open: http://localhost:5173
```

## Slack Usage

Mention `@PocketIA` in a channel or send a DM:

- `@PocketIA show me Alice Fontaine's portfolio`
- `@PocketIA which clients have policies renewing this week?`
- `@PocketIA who is most exposed to a Fed rate hike?`
- `@PocketIA list all aggressive clients with over $100k AUM`

## Proactive Alerts

The scheduler runs daily at 08:00 UTC and posts to `#wealth-alerts`:
- Policies renewing within 7 days (with urgency color coding)

Trigger a manual market impact alert from code:
```python
from slack_bot.handlers.alert_handler import post_market_impact_alert
post_market_impact_alert(
    slack_client,
    event_description="Fed rate hike 50bps",
    affected_asset_classes=["Fixed Income"],
    threshold_pct=20.0,
)
```

## Adding a New Custodian

1. Create `ingestion/parsers/custodian_c.py` implementing `BaseCustodianParser.parse()`
2. Register it in `ingestion/run_ingestion.py` PARSERS dict

## Adding a New Tool

1. Implement the Python function in `agent_tools/your_tool.py`
2. Add the JSON schema to `agent_tools/tool_registry.py` TOOLS list
3. Register the function in `slack_bot/tool_dispatcher.py` TOOL_MAP
