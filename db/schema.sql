-- Pocket IA: Unified Client Knowledge Graph Schema
-- Clients live in Zoho CRM. Holdings, Policies, and Portfolio Snapshots live here.

CREATE TABLE IF NOT EXISTS holdings (
    holding_id    SERIAL PRIMARY KEY,
    client_id     VARCHAR(50)    NOT NULL,
    ticker        VARCHAR(20),
    security_name TEXT           NOT NULL,
    isin          VARCHAR(20),
    asset_class   VARCHAR(50),
    sector        VARCHAR(100),
    geography     VARCHAR(50),
    account_type  VARCHAR(30),
    quantity      NUMERIC(18, 6),
    market_value  NUMERIC(18, 2),
    currency      VARCHAR(10)    DEFAULT 'USD',
    custodian     VARCHAR(100),
    as_of_date    DATE           NOT NULL,
    ingested_at   TIMESTAMPTZ    DEFAULT NOW(),
    UNIQUE (client_id, security_name, account_type, as_of_date)
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id       VARCHAR(50)  PRIMARY KEY,
    client_id       VARCHAR(50)  NOT NULL,
    policy_type     VARCHAR(50),
    insurer         TEXT,
    coverage_amount NUMERIC(18, 2),
    premium         NUMERIC(10, 2),
    renewal_date    DATE,
    status          VARCHAR(20)  DEFAULT 'active'
);

-- Derived portfolio analytics — one row per (portfolio_name, as_of_date)
-- portfolio_name is a stable identifier across multiple upload periods
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    snapshot_id          SERIAL        PRIMARY KEY,
    portfolio_name       VARCHAR(200)  NOT NULL,
    zoho_client_id       VARCHAR(50),
    source_file          VARCHAR(200),
    as_of_date           DATE          NOT NULL,
    total_value          NUMERIC(18, 2),
    asset_allocation     JSONB,
    sector_concentration JSONB,
    geographic_exposure  JSONB,
    top_10_holdings      JSONB,
    risk_metrics         JSONB,
    ingested_at          TIMESTAMPTZ   DEFAULT NOW(),
    UNIQUE (portfolio_name, as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_holdings_client       ON holdings(client_id);
CREATE INDEX IF NOT EXISTS idx_holdings_date         ON holdings(as_of_date);
CREATE INDEX IF NOT EXISTS idx_policies_renewal      ON policies(renewal_date);
CREATE INDEX IF NOT EXISTS idx_policies_client       ON policies(client_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio   ON portfolio_snapshots(portfolio_name);
CREATE INDEX IF NOT EXISTS idx_snapshots_date        ON portfolio_snapshots(as_of_date);
