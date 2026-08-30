// Server-side Postgres pool (Neon). Only imported by /app/api routes — never
// by client components. The connection string lives in .env.local (gitignored).

import { Pool } from "pg";

const connectionString = process.env.DATABASE_URL;

export const pool = connectionString
  ? new Pool({
      connectionString,
      ssl: { rejectUnauthorized: false },
      max: 5,
    })
  : null;

const SCHEMA = `
CREATE TABLE IF NOT EXISTS agent_sessions (
  id text PRIMARY KEY,
  kind text NOT NULL DEFAULT 'explore',
  title text,
  symbol text,
  snapshot jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS agent_sessions_updated_at_idx
  ON agent_sessions (updated_at DESC);
`;

let ensured: Promise<void> | null = null;

export function ensureSchema(): Promise<void> {
  if (!ensured) {
    ensured = (async () => {
      if (!pool) return;
      await pool.query(SCHEMA);
    })();
  }
  return ensured;
}