// Client-side session archive: shared data shapes + fetch/save helpers for the
// /api/sessions routes (which persist to Neon Postgres server-side).

import type { ActivityState } from "./agent";

export interface ResolvedFormats {
  input: string;
  instrument_name: string;
  news_symbol: string;
  ta_symbol: string;
  errors: string[];
}

export interface Evidence {
  news_symbol: string;
  ta_symbol: string;
  news: {
    sentiment_score: number | null;
    sentiment_label: string | null;
    sentiment_trend: string | null;
    source_divergence: string | null;
    headline_count: number | null;
    top_headlines: string[];
  } | null;
  technical: {
    trend: string | null;
    rsi: number | null;
    macd_signal: string | null;
    volatility_atr: number | null;
    support: number | null;
    resistance: number | null;
    verdict: string | null;
    verdict_stability: string | null;
    suggested_stop_loss: number | null;
    suggested_take_profit: number | null;
  } | null;
  errors: string[];
}

export interface Synthesis {
  combined_signal:
    | "strong_long"
    | "strong_short"
    | "conflict_reduce"
    | "no_trade"
    | null;
  confidence: "high" | "medium" | "low" | null;
  rationale: string | null;
  recommended_size_note: string | null;
  errors: string[];
}

export interface Proposal {
  proposal_id: string | null;
  direction: "buy" | "sell" | null;
  broker_symbol: string | null;
  size: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  risk_percent_used: number | null;
  kill_switch_on: boolean | null;
  within_position_cap: boolean | null;
  expires_at: string | null;
  errors: string[];
}

export interface Position {
  broker_symbol: string;
  direction: string;
  size: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  stop_loss: number;
  take_profit: number;
}

export interface TradeRecord {
  id: string;
  timestamp: string;
  symbol: string;
  direction: string;
  size: number;
  fill_price: number | null;
  combined_signal: string | null;
}

export interface SessionSummary {
  id: string;
  title: string | null;
  symbol: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SessionSnapshotData {
  symbol: string;
  resolved: ResolvedFormats | null;
  evidence: Evidence | null;
  synthesis: Synthesis | null;
  proposal: Proposal | null;
  positions: Position[];
  history: TradeRecord[];
  activity: ActivityState;
}

export async function listSessions(): Promise<SessionSummary[]> {
  const res = await fetch("/api/sessions");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = (await res.json()) as { sessions: SessionSummary[] };
  return json.sessions;
}

export async function fetchSession(
  id: string,
): Promise<{ session: SessionSummary; snapshot: SessionSnapshotData }> {
  const res = await fetch(`/api/sessions/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as {
    session: SessionSummary;
    snapshot: SessionSnapshotData;
  };
}

export async function saveSession(
  id: string,
  snapshot: SessionSnapshotData,
  meta?: { kind?: string; title?: string | null; symbol?: string | null },
): Promise<void> {
  const res = await fetch(`/api/sessions/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind: meta?.kind ?? "explore",
      title: meta?.title ?? null,
      symbol: meta?.symbol ?? null,
      snapshot,
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`/api/sessions/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}