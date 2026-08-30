"use client";

import { useEffect, useRef, useState } from "react";

/* ---------------------------------------------------------------------- */
/* Types — mirror the JSON contracts the /api/agent route enforces         */
/* ---------------------------------------------------------------------- */

interface Preflight {
  bridge_alive: boolean | null;
  kill_switch_on: boolean | null;
  max_risk_percent: number | null;
  position_caps: string | null;
  account: {
    balance: number;
    equity: number;
    margin: number;
    leverage: number;
  } | null;
  errors: string[];
}

interface ResolvedFormats {
  input: string;
  instrument_name: string;
  news_symbol: string;
  ta_symbol: string;
  errors: string[];
}

interface Evidence {
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

interface Synthesis {
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

interface Proposal {
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

interface ExecutionResult {
  executed: boolean | null;
  order_id: string | null;
  fill_price: number | null;
  broker_symbol: string | null;
  direction: string | null;
  size: number | null;
  account_after: { balance: number; equity: number; margin: number } | null;
  errors: string[];
}

interface Position {
  broker_symbol: string;
  direction: string;
  size: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  stop_loss: number;
  take_profit: number;
}

interface TradeRecord {
  id: string;
  timestamp: string;
  symbol: string;
  direction: string;
  size: number;
  fill_price: number | null;
  combined_signal: string | null;
}

const HISTORY_KEY = "trading-agent-trade-history";

/* ---------------------------------------------------------------------- */
/* One call = one action = one engineered turn                             */
/* ---------------------------------------------------------------------- */
async function callAgent(
  action: string,
  params: Record<string, any>,
  sessionId: string | null,
) {
  const res = await fetch("/api/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, params, sessionId }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json?.error ?? `HTTP ${res.status}`);
  return json as {
    sessionId: string;
    ok: boolean;
    data: any;
    raw?: string;
    error?: string;
  };
}

/* ---------------------------------------------------------------------- */
/* Tiny inline line-icons — no icon library dependency                     */
/* ---------------------------------------------------------------------- */
function Ic({ name, className = "" }: { name: string; className?: string }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  const paths: Record<string, JSX.Element> = {
    compass: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M14.5 9.5 12.8 14 8 15.5l1.7-4.5z" />
      </>
    ),
    stack: (
      <>
        <path d="M12 3 3 8l9 5 9-5-9-5Z" />
        <path d="M3 13l9 5 9-5" />
      </>
    ),
    trend: (
      <>
        <path d="M3 17 9 11l4 4 8-8" />
        <path d="M15 7h6v6" />
      </>
    ),
    shield: <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" />,
    gear: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
      </>
    ),
    refresh: (
      <>
        <path d="M4 12a8 8 0 0 1 14-5.3L20 8" />
        <path d="M20 4v4h-4" />
        <path d="M20 12a8 8 0 0 1-14 5.3L4 16" />
        <path d="M4 20v-4h4" />
      </>
    ),
    arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
    x: <path d="M6 6l12 12M18 6 6 18" />,
    up: <path d="M6 15l6-6 6 6" />,
    down: <path d="M6 9l6 6 6-6" />,
    dot: <circle cx="12" cy="12" r="4" />,
    globe: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18M12 3c2.5 2.6 2.5 15.4 0 18M12 3c-2.5 2.6-2.5 15.4 0 18" />
      </>
    ),
  };
  return (
    <svg viewBox="0 0 24 24" className={className} {...common}>
      {paths[name] ?? null}
    </svg>
  );
}

/* ---------------------------------------------------------------------- */
/* Palette-matched building blocks                                         */
/* ---------------------------------------------------------------------- */

function Panel({
  title,
  subtitle,
  className = "",
  right,
  children,
}: {
  title: string;
  subtitle?: string;
  className?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`rounded-[28px] bg-white p-6 shadow-[0_10px_30px_rgba(31,42,40,0.06)] ${className}`}
    >
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h3 className="text-[15px] font-bold text-[#20302c]">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-xs text-[#8a978f]">{subtitle}</p>
          )}
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

function IconBtn({
  onClick,
  name,
  spinning,
}: {
  onClick: () => void;
  name: string;
  spinning?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className="rounded-full bg-[#f2efe6] p-2 text-[#5c6b64] transition hover:bg-[#e9e4d5]"
    >
      <Ic name={name} className={`h-4 w-4 ${spinning ? "animate-spin" : ""}`} />
    </button>
  );
}

export default function TradingDashboard() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  const [preflight, setPreflight] = useState<Preflight | null>(null);

  const [query, setQuery] = useState("");
  const [stage, setStage] = useState<string | null>(null); // status line under the input
  const [resolved, setResolved] = useState<ResolvedFormats | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [synthesis, setSynthesis] = useState<Synthesis | null>(null);
  const [exploreError, setExploreError] = useState<string | null>(null);

  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [autonomous, setAutonomous] = useState(false);

  const [positions, setPositions] = useState<Position[]>([]);
  const [history, setHistory] = useState<TradeRecord[]>([]);
  const [tab, setTab] = useState<"history" | "open">("history");

  const heroRef = useRef<HTMLDivElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const signalsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      if (raw) setHistory(JSON.parse(raw));
    } catch {}
    runPreflight();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function persistHistory(next: TradeRecord[]) {
    setHistory(next);
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
    } catch {}
  }

  function setB(key: string, v: boolean) {
    setBusy((p) => ({ ...p, [key]: v }));
  }

  const killSwitchOn = preflight?.kill_switch_on === true;

  async function runPreflight() {
    setB("preflight", true);
    try {
      const res = await callAgent("preflight", {}, sessionId);
      setSessionId(res.sessionId);
      setPreflight(
        res.ok
          ? res.data
          : {
              bridge_alive: false,
              kill_switch_on: null,
              max_risk_percent: null,
              position_caps: null,
              account: null,
              errors: [res.error ?? "unreadable response"],
            },
      );
    } finally {
      setB("preflight", false);
    }
  }

  async function runExplore() {
    if (!query.trim()) return;
    setExploreError(null);
    setResolved(null);
    setEvidence(null);
    setSynthesis(null);
    setProposal(null);
    let sid = sessionId;

    setStage("figuring out the right symbols…");
    setB("explore", true);
    try {
      const r1 = await callAgent(
        "resolve_formats",
        { query: query.trim() },
        sid,
      );
      sid = r1.sessionId;
      setSessionId(sid);
      if (!r1.ok) {
        setExploreError(r1.error ?? "Could not resolve that instrument.");
        return;
      }
      setResolved(r1.data);

      setStage("reading the tape & the headlines…");
      const r2 = await callAgent(
        "evidence",
        { newsSymbol: r1.data.news_symbol, taSymbol: r1.data.ta_symbol },
        sid,
      );
      sid = r2.sessionId;
      setSessionId(sid);
      if (!r2.ok) {
        setExploreError(r2.error ?? "Couldn't pull the evidence.");
        return;
      }
      setEvidence(r2.data);

      setStage("weighing it up…");
      const r3 = await callAgent("synthesize", { evidence: r2.data }, sid);
      sid = r3.sessionId;
      setSessionId(sid);
      if (!r3.ok) {
        setExploreError(r3.error ?? "Couldn't land on a call.");
        return;
      }
      setSynthesis(r3.data);
    } finally {
      setStage(null);
      setB("explore", false);
    }
  }

  async function runPropose(direction: "buy" | "sell") {
    if (!resolved || killSwitchOn) return;
    setB("propose", true);
    try {
      const res = await callAgent(
        "propose",
        {
          instrumentName: resolved.instrument_name,
          direction,
          evidence,
          synthesis,
        },
        sessionId,
      );
      setSessionId(res.sessionId);
      setProposal(
        res.ok
          ? res.data
          : {
              proposal_id: null,
              direction,
              broker_symbol: null,
              size: null,
              stop_loss: null,
              take_profit: null,
              risk_percent_used: null,
              kill_switch_on: null,
              within_position_cap: null,
              expires_at: null,
              errors: [res.error ?? "unreadable response"],
            },
      );
      setConfirmText("");
    } finally {
      setB("propose", false);
    }
  }

  async function runExecute() {
    if (!proposal?.proposal_id || killSwitchOn) return;
    if (!autonomous && confirmText.trim().toUpperCase() !== "CONFIRM") return;
    setB("execute", true);
    try {
      const res = await callAgent(
        "execute",
        { proposalId: proposal.proposal_id },
        sessionId,
      );
      setSessionId(res.sessionId);
      const result: ExecutionResult | null = res.ok ? res.data : null;
      if (result?.executed) {
        persistHistory([
          {
            id: result.order_id ?? crypto.randomUUID(),
            timestamp: new Date().toISOString(),
            symbol: result.broker_symbol ?? proposal.broker_symbol ?? "",
            direction: result.direction ?? proposal.direction ?? "",
            size: result.size ?? proposal.size ?? 0,
            fill_price: result.fill_price,
            combined_signal: synthesis?.combined_signal ?? null,
          },
          ...history,
        ]);
        setProposal(null);
        setConfirmText("");
        runPositions();
      } else {
        alert(
          "The agent didn't confirm a fill — nothing was logged. Check the errors on the proposal.",
        );
      }
    } finally {
      setB("execute", false);
    }
  }

  async function runPositions() {
    setB("positions", true);
    try {
      const res = await callAgent("positions", {}, sessionId);
      setSessionId(res.sessionId);
      setPositions(res.ok ? (res.data?.positions ?? []) : []);
    } finally {
      setB("positions", false);
    }
  }

  function scrollTo(ref: React.RefObject<HTMLDivElement>) {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // -- derived visuals ------------------------------------------------

  const signalWord =
    synthesis?.combined_signal === "strong_long"
      ? "BULLISH"
      : synthesis?.combined_signal === "strong_short"
        ? "BEARISH"
        : synthesis?.combined_signal === "conflict_reduce"
          ? "MIXED"
          : synthesis?.combined_signal === "no_trade"
            ? "NO EDGE"
            : "—";

  const canTrade =
    synthesis?.combined_signal === "strong_long" ||
    synthesis?.combined_signal === "strong_short";
  const suggestedDirection: "buy" | "sell" =
    synthesis?.combined_signal === "strong_short" ? "sell" : "buy";

  const sentimentBar =
    evidence?.news?.sentiment_score != null
      ? Math.max(0, Math.min(100, (evidence.news.sentiment_score + 1) * 50))
      : 0;
  const rsiBar =
    evidence?.technical?.rsi != null
      ? Math.max(0, Math.min(100, evidence.technical.rsi))
      : 0;
  const confidenceBar =
    synthesis?.confidence === "high"
      ? 90
      : synthesis?.confidence === "medium"
        ? 58
        : synthesis?.confidence === "low"
          ? 28
          : 0;
  const riskBar =
    proposal?.risk_percent_used != null && preflight?.max_risk_percent
      ? Math.max(
          0,
          Math.min(
            100,
            (proposal.risk_percent_used / preflight.max_risk_percent) * 100,
          ),
        )
      : 0;

  const bars = [
    { label: "Sentiment", value: sentimentBar },
    { label: "RSI", value: rsiBar },
    { label: "Confidence", value: confidenceBar },
    { label: "Risk used", value: riskBar },
  ];

  const riskUsedPct = proposal?.risk_percent_used ?? 0;
  const riskMax = preflight?.max_risk_percent ?? 0;
  const riskArc =
    riskMax > 0 ? Math.max(0, Math.min(1, riskUsedPct / riskMax)) : 0;
  const riskCircumference = 2 * Math.PI * 40;

  const levels = evidence?.technical
    ? [
        evidence.technical.support,
        evidence.technical.suggested_stop_loss,
        evidence.technical.suggested_take_profit,
        evidence.technical.resistance,
      ].filter((v): v is number => v != null)
    : [];
  const levelMin = levels.length ? Math.min(...levels) : 0;
  const levelMax = levels.length ? Math.max(...levels) : 1;
  const pos = (v: number) =>
    levelMax === levelMin ? 50 : ((v - levelMin) / (levelMax - levelMin)) * 100;

  return (
    <div className="flex min-h-screen bg-[#f6f2e9] text-[#20302c]">
      {/* ---------------- SIDEBAR ---------------- */}
      <aside className="relative flex w-[240px] shrink-0 flex-col overflow-hidden bg-[#2c463f] px-5 py-7 text-[#dfe8e3]">
        <svg
          className="pointer-events-none absolute -left-10 top-24 h-64 w-64 opacity-[0.07]"
          viewBox="0 0 200 200"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
        >
          <path d="M-20 60 Q60 20 100 80 T220 60" />
          <path d="M-20 100 Q60 60 100 120 T220 100" />
          <path d="M-20 140 Q60 100 100 160 T220 140" />
        </svg>

        <div className="relative mb-8 flex items-center gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#e3a94d] text-sm font-bold text-[#2c463f]">
            TA
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-white">
              Trading Agent
            </div>
            <div className="truncate text-[11px] text-[#a9beb5]">
              {sessionId ? `session · ${sessionId.slice(0, 8)}` : "connecting…"}
            </div>
          </div>
        </div>

        <nav className="relative flex flex-col gap-1 text-[13px] font-medium">
          {[
            { label: "Overview", icon: "compass", ref: heroRef },
            { label: "Trade Log", icon: "stack", ref: logRef },
            { label: "Signals", icon: "trend", ref: signalsRef },
          ].map((item, i) => (
            <button
              key={item.label}
              onClick={() => scrollTo(item.ref)}
              className={`flex items-center gap-3 rounded-2xl px-4 py-2.5 text-left transition ${i === 0 ? "bg-[#f6f2e9] text-[#2c463f]" : "text-[#c3d3cb] hover:bg-white/5"}`}
            >
              <Ic name={item.icon} className="h-4 w-4" />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="relative mt-auto pt-8">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[#8ea79b]">
            Connections
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`grid h-8 w-8 place-items-center rounded-full border-2 border-[#2c463f] text-[10px] font-bold text-white ${preflight?.bridge_alive ? "bg-[#3f9a8f]" : "bg-[#7a6b53]"}`}
            >
              MT5
            </div>
            <div className="grid h-8 w-8 place-items-center rounded-full border-2 border-[#2c463f] bg-[#e3a94d] text-[10px] font-bold text-[#2c463f]">
              NS
            </div>
            <div className="grid h-8 w-8 place-items-center rounded-full border-2 border-[#2c463f] bg-[#3f9a8f] text-[10px] font-bold text-white">
              TA
            </div>
            <span
              className={`ml-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${killSwitchOn ? "bg-[#c65b4e] text-white" : "bg-white/10 text-[#c3d3cb]"}`}
            >
              {killSwitchOn ? "kill on" : "live"}
            </span>
          </div>
        </div>
      </aside>

      {/* ---------------- MAIN ---------------- */}
      <main className="flex-1 overflow-y-auto px-8 py-7">
        {/* Explore bar */}
        <div className="mb-6 flex items-center gap-3 rounded-full bg-white px-3 py-2 shadow-[0_10px_30px_rgba(31,42,40,0.06)]">
          <Ic name="compass" className="ml-2 h-4 w-4 text-[#8a978f]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runExplore()}
            placeholder="What do you want to explore today? Bitcoin, Apple, gold…"
            className="flex-1 bg-transparent text-sm text-[#20302c] placeholder-[#a3ada6] focus:outline-none"
          />
          {stage && (
            <span className="hidden text-xs text-[#8a978f] sm:inline">
              {stage}
            </span>
          )}
          <button
            onClick={runExplore}
            disabled={!query.trim() || busy.explore}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#2c463f] text-white transition hover:bg-[#20342f] disabled:opacity-30"
          >
            <Ic
              name={busy.explore ? "refresh" : "arrow"}
              className={`h-4 w-4 ${busy.explore ? "animate-spin" : ""}`}
            />
          </button>
        </div>
        {exploreError && (
          <p className="-mt-4 mb-6 text-xs text-[#c65b4e]">⚠ {exploreError}</p>
        )}

        {/* Hero row */}
        <div
          ref={heroRef}
          className="mb-5 grid grid-cols-1 gap-5 md:grid-cols-3"
        >
          <div className="rounded-[28px] bg-[#e3a94d] p-6 text-[#3a2c10]">
            <div className="mb-8 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide opacity-70">
                Today's read
              </span>
              <Ic
                name={
                  synthesis?.combined_signal === "strong_short" ? "down" : "up"
                }
                className="h-5 w-5 opacity-70"
              />
            </div>
            <div className="text-2xl font-extrabold">
              {resolved?.instrument_name ?? "—"}
            </div>
            <div className="mt-1 text-sm font-semibold opacity-80">
              {signalWord}
            </div>
          </div>

          <div className="rounded-[28px] bg-[#3f9a8f] p-6 text-white">
            <div className="mb-8 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide opacity-80">
                Confidence
              </span>
              <Ic name="shield" className="h-5 w-5 opacity-80" />
            </div>
            <div className="text-2xl font-extrabold capitalize">
              {synthesis?.confidence ?? "—"}
            </div>
            <div className="mt-1 text-sm opacity-80">
              {evidence?.news?.sentiment_trend
                ? `sentiment ${evidence.news.sentiment_trend}`
                : "awaiting a read"}
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[28px] bg-white p-6">
            <Ic
              name="globe"
              className="pointer-events-none absolute -right-6 -top-6 h-32 w-32 text-[#eee7d6]"
            />
            <div className="relative mb-8 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide text-[#8a978f]">
                Open positions
              </span>
              <IconBtn
                name="refresh"
                onClick={runPositions}
                spinning={busy.positions}
              />
            </div>
            <div className="relative text-2xl font-extrabold text-[#20302c]">
              {positions.length}
            </div>
            <div className="relative mt-1 text-sm text-[#8a978f]">
              {preflight?.account
                ? `equity $${preflight.account.equity.toLocaleString()}`
                : "checking account…"}
            </div>
          </div>
        </div>

        {/* Trade pill / hold-off note, tied to the synthesis */}
        {synthesis && (
          <div className="mb-5 flex flex-wrap items-center gap-3 rounded-[24px] bg-white px-6 py-4 shadow-[0_10px_30px_rgba(31,42,40,0.06)]">
            <p className="flex-1 text-sm text-[#4a5751]">
              {synthesis.rationale}
            </p>
            {killSwitchOn ? (
              <span className="rounded-full bg-[#f3e2df] px-4 py-2 text-xs font-semibold text-[#c65b4e]">
                kill switch is on — no trading right now
              </span>
            ) : canTrade ? (
              <button
                onClick={() => runPropose(suggestedDirection)}
                disabled={busy.propose}
                className={`rounded-full px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-40 ${suggestedDirection === "buy" ? "bg-[#3f9a8f] hover:bg-[#33847a]" : "bg-[#c65b4e] hover:bg-[#b34e42]"}`}
              >
                {busy.propose
                  ? "sizing it up…"
                  : `Take the trade · ${suggestedDirection}`}
              </button>
            ) : (
              <span className="rounded-full bg-[#f2efe6] px-4 py-2 text-xs font-semibold text-[#8a978f]">
                agent says: hold off
              </span>
            )}
          </div>
        )}

        {/* Proposal confirm strip */}
        {proposal && (
          <div className="mb-5 flex flex-wrap items-center gap-3 rounded-[24px] border border-[#e3a94d]/40 bg-[#fdf6e8] px-6 py-4">
            <div className="flex-1 text-sm text-[#5c4a20]">
              <span className="font-semibold">{proposal.broker_symbol}</span> ·{" "}
              {proposal.direction} · {proposal.size} lots · SL{" "}
              {proposal.stop_loss} / TP {proposal.take_profit}
            </div>
            {proposal.errors?.length > 0 && (
              <span className="text-xs text-[#c65b4e]">
                {proposal.errors[0]}
              </span>
            )}
            {!autonomous && (
              <input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="type CONFIRM"
                className="w-32 rounded-full border border-[#e3a94d]/50 bg-white px-3 py-1.5 text-xs focus:outline-none"
              />
            )}
            <button
              onClick={() => setAutonomous((a) => !a)}
              className={`rounded-full px-3 py-1.5 text-[11px] font-semibold ${autonomous ? "bg-[#2c463f] text-white" : "bg-white text-[#8a978f]"}`}
            >
              auto
            </button>
            <button
              onClick={runExecute}
              disabled={
                busy.execute ||
                (!autonomous && confirmText.trim().toUpperCase() !== "CONFIRM")
              }
              className="rounded-full bg-[#2c463f] px-4 py-1.5 text-xs font-semibold text-white disabled:opacity-30"
            >
              {busy.execute ? "sending…" : "Execute"}
            </button>
            <button
              onClick={() => setProposal(null)}
              className="rounded-full p-1.5 text-[#8a978f] hover:bg-white/60"
            >
              <Ic name="x" className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Row 2: Trade log (wide) + Snapshot */}
        <div className="mb-5 grid grid-cols-1 gap-5 md:grid-cols-3">
          <div ref={logRef} className="md:col-span-2">
            <Panel
              title="Trade Log"
              subtitle="History and anything still open"
              right={
                <div className="flex gap-1 rounded-full bg-[#f2efe6] p-1 text-xs font-semibold">
                  <button
                    onClick={() => setTab("history")}
                    className={`rounded-full px-3 py-1 ${tab === "history" ? "bg-white text-[#20302c] shadow-sm" : "text-[#8a978f]"}`}
                  >
                    History
                  </button>
                  <button
                    onClick={() => setTab("open")}
                    className={`rounded-full px-3 py-1 ${tab === "open" ? "bg-white text-[#20302c] shadow-sm" : "text-[#8a978f]"}`}
                  >
                    Open
                  </button>
                </div>
              }
            >
              {tab === "history" ? (
                history.length === 0 ? (
                  <p className="py-6 text-center text-sm text-[#8a978f]">
                    No trades yet — explore something above and take the call
                    when it looks right.
                  </p>
                ) : (
                  <div className="space-y-1">
                    {history.slice(0, 6).map((t) => (
                      <div
                        key={t.id}
                        className="flex items-center gap-3 rounded-2xl px-2 py-2.5 hover:bg-[#f6f2e9]"
                      >
                        <div
                          className={`grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold text-white ${t.direction === "buy" ? "bg-[#3f9a8f]" : "bg-[#c65b4e]"}`}
                        >
                          {t.direction === "buy" ? "B" : "S"}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-semibold text-[#20302c]">
                            {t.symbol}
                          </div>
                          <div className="text-xs text-[#8a978f]">
                            {new Date(t.timestamp).toLocaleDateString()}
                          </div>
                        </div>
                        <div className="text-right text-sm">
                          <div className="font-semibold text-[#20302c]">
                            {t.size} lots
                          </div>
                          <div className="text-xs text-[#8a978f]">
                            @ {t.fill_price ?? "—"}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              ) : positions.length === 0 ? (
                <p className="py-6 text-center text-sm text-[#8a978f]">
                  Nothing open right now.
                </p>
              ) : (
                <div className="space-y-1">
                  {positions.map((p) => (
                    <div
                      key={p.broker_symbol}
                      className="flex items-center gap-3 rounded-2xl px-2 py-2.5 hover:bg-[#f6f2e9]"
                    >
                      <div
                        className={`grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold text-white ${p.direction === "buy" ? "bg-[#3f9a8f]" : "bg-[#c65b4e]"}`}
                      >
                        {p.direction === "buy" ? "B" : "S"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-semibold text-[#20302c]">
                          {p.broker_symbol}
                        </div>
                        <div className="text-xs text-[#8a978f]">
                          entry {p.entry_price}
                        </div>
                      </div>
                      <div
                        className={`text-sm font-semibold ${p.pnl >= 0 ? "text-[#3f9a8f]" : "text-[#c65b4e]"}`}
                      >
                        {p.pnl >= 0 ? "+" : ""}
                        {p.pnl}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>

          <Panel title="Snapshot" subtitle="This session's read">
            <div className="flex h-40 items-end justify-between gap-3">
              {bars.map((b) => (
                <div
                  key={b.label}
                  className="flex flex-1 flex-col items-center gap-2"
                >
                  <div className="flex h-32 w-full items-end overflow-hidden rounded-full bg-[#f2efe6]">
                    <div
                      className="w-full rounded-full bg-[#3f9a8f] transition-all"
                      style={{ height: `${b.value}%` }}
                    />
                  </div>
                  <span className="text-center text-[10px] leading-tight text-[#8a978f]">
                    {b.label}
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        </div>

        {/* Row 3: Risk donut + Price levels */}
        <div ref={signalsRef} className="grid grid-cols-1 gap-5 md:grid-cols-3">
          <Panel title="Risk Usage" subtitle="Of your max per-trade cap">
            <div className="flex items-center justify-center py-2">
              <svg viewBox="0 0 100 100" className="h-36 w-36 -rotate-90">
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="#f2efe6"
                  strokeWidth="12"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="#e3a94d"
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray={riskCircumference}
                  strokeDashoffset={riskCircumference * (1 - riskArc)}
                />
              </svg>
            </div>
            <div className="-mt-24 mb-16 text-center">
              <div className="text-xl font-extrabold text-[#20302c]">
                {riskUsedPct ? `${riskUsedPct}%` : "0%"}
              </div>
              <div className="text-[10px] text-[#8a978f]">
                of {riskMax || "—"}% cap
              </div>
            </div>
          </Panel>

          <div className="md:col-span-2">
            <Panel
              title="Price Levels"
              subtitle={
                evidence
                  ? `${evidence.ta_symbol} · support to resistance`
                  : "Explore a symbol to see this"
              }
            >
              {levels.length >= 2 ? (
                <div className="relative mt-6 pb-6">
                  {evidence?.technical?.verdict && (
                    <div className="absolute -top-2 left-1/2 -translate-x-1/2 rounded-full bg-[#2c463f] px-3 py-1 text-[11px] font-semibold text-white">
                      {evidence.technical.verdict} verdict
                    </div>
                  )}
                  <div className="relative mt-10 h-1.5 rounded-full bg-[#f2efe6]">
                    <div
                      className="absolute inset-y-0 rounded-full bg-gradient-to-r from-[#c65b4e] via-[#e3a94d] to-[#3f9a8f]"
                      style={{ left: 0, right: 0 }}
                    />
                    {evidence?.technical?.support != null && (
                      <div
                        className="absolute -top-7 flex -translate-x-1/2 flex-col items-center text-[10px] text-[#8a978f]"
                        style={{ left: `${pos(evidence.technical.support)}%` }}
                      >
                        <span>support</span>
                        <span className="font-semibold text-[#20302c]">
                          {evidence.technical.support}
                        </span>
                      </div>
                    )}
                    {evidence?.technical?.suggested_stop_loss != null && (
                      <div
                        className="absolute -bottom-7 flex -translate-x-1/2 flex-col items-center text-[10px] text-[#8a978f]"
                        style={{
                          left: `${pos(evidence.technical.suggested_stop_loss)}%`,
                        }}
                      >
                        <span className="font-semibold text-[#c65b4e]">
                          {evidence.technical.suggested_stop_loss}
                        </span>
                        <span>stop</span>
                      </div>
                    )}
                    {evidence?.technical?.suggested_take_profit != null && (
                      <div
                        className="absolute -bottom-7 flex -translate-x-1/2 flex-col items-center text-[10px] text-[#8a978f]"
                        style={{
                          left: `${pos(evidence.technical.suggested_take_profit)}%`,
                        }}
                      >
                        <span className="font-semibold text-[#3f9a8f]">
                          {evidence.technical.suggested_take_profit}
                        </span>
                        <span>target</span>
                      </div>
                    )}
                    {evidence?.technical?.resistance != null && (
                      <div
                        className="absolute -top-7 flex -translate-x-1/2 flex-col items-center text-[10px] text-[#8a978f]"
                        style={{
                          left: `${pos(evidence.technical.resistance)}%`,
                        }}
                      >
                        <span>resistance</span>
                        <span className="font-semibold text-[#20302c]">
                          {evidence.technical.resistance}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <p className="py-10 text-center text-sm text-[#8a978f]">
                  Nothing to plot yet.
                </p>
              )}
            </Panel>
          </div>
        </div>
      </main>
    </div>
  );
}
