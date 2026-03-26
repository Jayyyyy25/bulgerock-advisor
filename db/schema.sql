-- Pocket IA: Unified Client Knowledge Graph Schema

CREATE TABLE IF NOT EXISTS clients (
    client_id       VARCHAR(50) PRIMARY KEY,
    full_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    risk_profile    VARCHAR(20) CHECK (risk_profile IN ('conservative', 'moderate', 'aggressive')),
    advisor_id      VARCHAR(50),
    aum             NUMERIC(18, 2) DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS holdings (
    holding_id      SERIAL PRIMARY KEY,
    client_id       VARCHAR(50) NOT NULL REFERENCES clients(client_id),
    ticker          VARCHAR(20) NOT NULL,
    security_name   TEXT,
    isin            VARCHAR(20),
    asset_class     VARCHAR(50),
    sector          VARCHAR(100),
    account_type    VARCHAR(30),
    quantity        NUMERIC(18, 6),
    market_value    NUMERIC(18, 2),
    currency        VARCHAR(10) DEFAULT 'USD',
    custodian       VARCHAR(50),
    as_of_date      DATE NOT NULL,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (client_id, ticker, account_type, as_of_date)
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id       VARCHAR(50) PRIMARY KEY,
    client_id       VARCHAR(50) NOT NULL REFERENCES clients(client_id),
    policy_type     VARCHAR(50),
    insurer         TEXT,
    coverage_amount NUMERIC(18, 2),
    premium         NUMERIC(10, 2),
    renewal_date    DATE,
    status          VARCHAR(20) DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_holdings_client   ON holdings(client_id);
CREATE INDEX IF NOT EXISTS idx_holdings_date     ON holdings(as_of_date);
CREATE INDEX IF NOT EXISTS idx_policies_renewal  ON policies(renewal_date);
CREATE INDEX IF NOT EXISTS idx_policies_client   ON policies(client_id);
