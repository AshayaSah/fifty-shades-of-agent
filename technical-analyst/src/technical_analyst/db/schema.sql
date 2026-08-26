-- Run this once against your own Neon instance to set up the schema.
-- psql "$NEON_DATABASE_URL" -f src/technical_analyst/db/schema.sql

CREATE TABLE IF NOT EXISTS price_candles (
    symbol      TEXT NOT NULL,
    interval    TEXT NOT NULL,
    ts          TIMESTAMPTZ NOT NULL,
    open        NUMERIC NOT NULL,
    high        NUMERIC NOT NULL,
    low         NUMERIC NOT NULL,
    close       NUMERIC NOT NULL,
    volume      BIGINT NOT NULL,
    source      TEXT NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, interval, ts)
);

-- Append-only history: one row per completed analysis run. This is what
-- lets past analyses provide context (e.g. "verdict flipped bullish 3 days ago").
CREATE TABLE IF NOT EXISTS technical_analysis_reports (
    id                     BIGSERIAL PRIMARY KEY,
    symbol                 TEXT NOT NULL,
    interval               TEXT NOT NULL,
    as_of                  TIMESTAMPTZ NOT NULL,
    source                 TEXT NOT NULL,
    verdict                TEXT NOT NULL,
    confidence             NUMERIC NOT NULL,
    reasons                JSONB NOT NULL,
    support                NUMERIC,
    resistance             NUMERIC,
    suggested_stop_loss    NUMERIC,
    suggested_take_profit  NUMERIC,
    indicators             JSONB NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reports_symbol_asof
    ON technical_analysis_reports (symbol, as_of DESC);

-- One row per symbol, always overwritten with the newest report. Lets
-- "give me the current read on AAPL" skip scanning/sorting the history table.
CREATE TABLE IF NOT EXISTS latest_technical_analysis (
    symbol                 TEXT PRIMARY KEY,
    interval               TEXT NOT NULL,
    as_of                  TIMESTAMPTZ NOT NULL,
    source                 TEXT NOT NULL,
    verdict                TEXT NOT NULL,
    confidence             NUMERIC NOT NULL,
    reasons                JSONB NOT NULL,
    support                NUMERIC,
    resistance             NUMERIC,
    suggested_stop_loss    NUMERIC,
    suggested_take_profit  NUMERIC,
    indicators             JSONB NOT NULL,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
