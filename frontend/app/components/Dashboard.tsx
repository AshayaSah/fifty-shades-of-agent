"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode, RefObject } from "react";

import AgentActivity from "./AgentActivity";
import {
  streamAgent,
  type ActivityLogEntry,
  type ActivityState,
  type AgentEvent,
  type StreamResult,
} from "@/lib/agent";
import {
  deleteSession,
  fetchSession,
  listSessions,
  saveSession,
  type Evidence,
  type Position,
  type Proposal,
  type ResolvedFormats,
  type SessionSnapshotData,
  type SessionSummary,
  type Synthesis,
  type TradeRecord,
} from "@/lib/sessions";

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

const HISTORY_KEY = "trading-agent-trade-history";

/* Pipeline step number per action, matching the AgentActivity rail. */
const STEP: Record<string, number> = {
  preflight: 0,
  resolve_formats: 1,
  evidence: 2,
  synthesize: 3,
  propose: 4,
  execute: 5,
  positions: 6,
  close_position: 6,
};

const tailText = (s: string, n: number) =>
  s.length > n ? s.slice(s.length - n) : s;

const capLog = (log: ActivityLogEntry[]) =>
  log.length > 60 ? log.slice(log.length - 60) : log;

const relativeTime = (iso: string) => {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "now";
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
};

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
  const paths: Record<string, ReactNode> = {
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
    check: <path d="m5 13 4 4L19 7" />,
    alert: (
      <>
        <path d="M12 3 3 19h18L12 3Z" />
        <path d="M12 10v4" />
        <path d="M12 17.5v.01" />
      </>
    ),
    signal: (
      <>
        <path d="M5 12a7 7 0 0 1 14 0" />
        <path d="M8.5 12a3.5 3.5 0 0 1 7 0" />
        <path d="M12 12v.01" />
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
  right?: ReactNode;
  children: ReactNode;
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

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

interface ToastState {
  id: number;
  tone: "success" | "error" | "info";
  message: string;
}

export default function TradingDashboard() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  const [preflight, setPreflight] = useState<Preflight | null>(null);

  const [query, setQuery] = useState("");
  const [resolved, setResolved] = useState<ResolvedFormats | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [synthesis, setSynthesis] = useState<Synthesis | null>(null);
  const [exploreError, setExploreError] = useState<string | null>(null);

  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [autonomous, setAutonomous] = useState(false);

  const [positions, setPositions] = useState<Position[]>([]);
  const [history, setHistory] = useState<TradeRecord[]>(() => {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      return raw ? (JSON.parse(raw) as TradeRecord[]) : [];
    } catch {
      return [];
    }
  });
  const [tab, setTab] = useState<"history" | "open">("history");

  const [activity, setActivity] = useState<ActivityState>({
    running: false,
    step: 0,
    tools: [],
    text: "",
    reason: "",
    log: [],
    expanded: true,
  });
  const [connected, setConnected] = useState<string[]>([]);
  const [toast, setToast] = useState<ToastState | null>(null);

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [viewing, setViewing] = useState<{
    id: string;
    snapshot: SessionSnapshotData;
  } | null>(null);

  const heroRef = useRef<HTMLDivElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const signalsRef = useRef<HTMLDivElement>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const liveRef = useRef<SessionSnapshotData | null>(null);
  const exploreRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void refreshSessions();
    void runPreflight();
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

  function showToast(message: string, tone: ToastState["tone"] = "info") {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ id: Date.now(), tone, message });
    toastTimer.current = setTimeout(() => setToast(null), 5200);
  }

  /* ------------------------------------------------------------------ */
  /* Session archive (Neon-backed list + per-session snapshots)          */
  /* ------------------------------------------------------------------ */

  async function refreshSessions() {
    try {
      setSessions(await listSessions());
    } catch {
      /* sidebar stays as-is */
    }
  }

  function snapshotTitle(snap: SessionSnapshotData): string {
    const signal =
      snap.synthesis?.combined_signal != null
        ? snap.synthesis.combined_signal.replace(/_/g, " ")
        : snap.resolved?.instrument_name
          ? "explore"
          : null;
    return snap.symbol && signal
      ? `${snap.symbol} — ${signal}`
      : snap.symbol || "session";
  }

  function persistSnapshot(sid: string, extra: Partial<SessionSnapshotData>) {
    if (!sid || !liveRef.current) return;
    const snap: SessionSnapshotData = { ...liveRef.current, ...extra };
    const hasData =
      Boolean(snap.resolved) ||
      Boolean(snap.evidence) ||
      Boolean(snap.synthesis) ||
      Boolean(snap.proposal) ||
      snap.positions.length > 0 ||
      snap.history.length > 0;
    if (!hasData) return;
    const title = snapshotTitle(snap);
    const symbol = snap.symbol || null;
    void saveSession(sid, snap, { title, symbol }).catch(() => {});
    setSessions((prev) => {
      const found = prev.find((s) => s.id === sid);
      const row: SessionSummary = {
        id: sid,
        title,
        symbol,
        createdAt: found?.createdAt ?? new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      return found ? prev.map((s) => (s.id === sid ? row : s)) : [row, ...prev];
    });
  }

  async function viewSession(id: string) {
    if (viewing?.id === id) return;
    if (id === sessionId) {
      setViewing(null);
      return;
    }
    try {
      const { snapshot } = await fetchSession(id);
      setViewing({ id, snapshot });
    } catch {
      showToast("Couldn't load that session", "error");
    }
  }

  function resumeLive() {
    setViewing(null);
  }

  async function removeSession(id: string) {
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (viewing?.id === id) setViewing(null);
    } catch {
      showToast("Couldn't delete that session", "error");
    }
  }

  function startNewSession() {
    setViewing(null);
    setResolved(null);
    setEvidence(null);
    setSynthesis(null);
    setProposal(null);
    setPositions([]);
    setQuery("");
    setActivity(() => ({
      running: false,
      step: 0,
      tools: [],
      text: "",
      reason: "",
      log: [],
      expanded: true,
      error: undefined,
    }));
    requestAnimationFrame(() => exploreRef.current?.focus());
  }

  function toggleActivity() {
    if (viewing) {
      setViewing((v) =>
        v
          ? {
              ...v,
              snapshot: {
                ...v.snapshot,
                activity: {
                  ...v.snapshot.activity,
                  expanded: v.snapshot.activity.expanded !== false ? false : true,
                },
              },
            }
          : v,
      );
    } else {
      setActivity((a) => ({ ...a, expanded: a.expanded !== false ? false : true }));
    }
  }

  function clearActivity() {
    if (viewing) return;
    setActivity(() => ({
      running: false,
      step: 0,
      tools: [],
      text: "",
      reason: "",
      log: [],
      expanded: true,
      error: undefined,
    }));
  }

  function pushLog(entry: ActivityLogEntry) {
    setActivity((a) => ({ ...a, log: capLog([...a.log, entry]) }));
  }

  /* ------------------------------------------------------------------ */
  /* Live stream handling — drives the AgentActivity feed               */
  /* ------------------------------------------------------------------ */
  function handleStreamEvent(e: AgentEvent) {
    switch (e.type) {
      case "session.id":
        setSessionId(e.sessionId);
        break;
      case "action":
        setActivity((a) => ({
          ...a,
          running: true,
          action: e.action,
          label: e.label,
          hint: e.hint,
          step: STEP[e.action] ?? 0,
          tools: [],
          text: "",
          reason: "",
          error: undefined,
          expanded: true,
          log: capLog([
            ...a.log,
            { kind: "info", message: `Started ${e.label} — ${e.hint}` },
          ]),
        }));
        break;
      case "connecting":
        setConnected(e.servers);
        pushLog({ kind: "info", message: `Connected to ${e.servers.join(", ")}` });
        break;
      case "text":
        setActivity((a) => ({
          ...a,
          text: tailText((a.text + e.text).replace(/\s+/g, " ").trim(), 900),
        }));
        break;
      case "reason":
        setActivity((a) => ({
          ...a,
          reason: tailText((a.reason + e.text).replace(/\s+/g, " ").trim(), 700),
        }));
        break;
      case "tool.start":
        setActivity((a) => {
          const tools = [...a.tools];
          const i = tools.findIndex((t) => t.index === e.index);
          if (i >= 0) {
            tools[i] = {
              ...tools[i],
              id: e.id ?? tools[i].id,
              name: e.name,
              server: e.server ?? tools[i].server,
              status: "started",
            };
          } else {
            tools.push({
              index: e.index,
              id: e.id,
              name: e.name,
              server: e.server,
              status: "started",
            });
          }
          return {
            ...a,
            tools,
            log: capLog([...a.log, { kind: "tool", message: `→ ${e.name}` }]),
          };
        });
        break;
      case "tool.args":
        setActivity((a) => ({
          ...a,
          tools: a.tools.map((t) =>
            t.index === e.index && e.args
              ? { ...t, args: tailText(e.args, 500) }
              : t,
          ),
        }));
        break;
      case "tool.done":
        setActivity((a) => {
          let matched: string | undefined;
          const tools = a.tools.map((t) => {
            if (t.id === e.toolCallId || (!t.id && t.status === "started" && !matched)) {
              matched = t.name || t.id || "tool";
              return { ...t, status: "done" as const, content: e.content };
            }
            return t;
          });
          return {
            ...a,
            tools,
            log: capLog([...a.log, { kind: "tool", message: `✓ ${matched ?? "tool"}` }]),
          };
        });
        break;
      case "done":
        setActivity((a) => ({ ...a, running: false }));
        break;
      case "error":
        pushLog({ kind: "error", message: e.error });
        setActivity((a) => ({ ...a, running: false, error: e.error }));
        break;
    }
  }

  async function runAction(
    action: string,
    params: Record<string, unknown>,
    sid: string | null,
  ): Promise<StreamResult> {
    setB(action, true);
    setActivity((a) => ({ ...a, running: true, error: undefined }));
    try {
      const res = await streamAgent(action, params, sid ?? sessionId, handleStreamEvent);
      if (res.sessionId) setSessionId(res.sessionId);
      return res;
    } finally {
      setB(action, false);
    }
  }

  /* ------------------------------------------------------------------ */
  /* Actions                                                             */
  /* ------------------------------------------------------------------ */
  async function runPreflight() {
    const res = await runAction("preflight", {}, null);
    setPreflight(
      res.ok
        ? (res.data as Preflight)
        : {
            bridge_alive: false,
            kill_switch_on: null,
            max_risk_percent: null,
            position_caps: null,
            account: null,
            errors: [res.error ?? "unreadable response"],
          },
    );
  }

  async function runExplore() {
    if (!query.trim() || busy.explore) return;
    setExploreError(null);
    setViewing(null);
    setResolved(null);
    setEvidence(null);
    setSynthesis(null);
    setProposal(null);
    liveRef.current = {
      symbol: "",
      resolved: null,
      evidence: null,
      synthesis: null,
      proposal: null,
      positions: [],
      history: [],
      activity: {
        running: false,
        step: 0,
        tools: [],
        text: "",
        reason: "",
        log: [],
        expanded: true,
      },
    };
    const q = query.trim();

    const r1 = await runAction("resolve_formats", { query: q }, null);
    if (!r1.ok) {
      setExploreError(r1.error ?? "Could not resolve that instrument.");
      return;
    }
    const resolved = r1.data as ResolvedFormats;
    setResolved(resolved);
    persistSnapshot(r1.sessionId, {
      symbol: resolved.instrument_name,
      resolved,
      proposal: null,
    });

    const r2 = await runAction(
      "evidence",
      { newsSymbol: resolved.news_symbol, taSymbol: resolved.ta_symbol },
      r1.sessionId,
    );
    if (!r2.ok) {
      setExploreError(r2.error ?? "Couldn't pull the evidence.");
      return;
    }
    const evidenceData = r2.data as Evidence;
    setEvidence(evidenceData);
    persistSnapshot(r2.sessionId, { resolved, evidence: evidenceData });

    const r3 = await runAction("synthesize", { evidence: r2.data }, r2.sessionId);
    if (!r3.ok) {
      setExploreError(r3.error ?? "Couldn't land on a call.");
      return;
    }
    const synthesisData = r3.data as Synthesis;
    setSynthesis(synthesisData);
    persistSnapshot(r3.sessionId, {
      resolved,
      evidence: evidenceData,
      synthesis: synthesisData,
    });
  }

  async function runPropose(direction: "buy" | "sell") {
    if (!resolved || killSwitchOn) return;
    const res = await runAction(
      "propose",
      { instrumentName: resolved.instrument_name, direction, evidence, synthesis },
      sessionId,
    );
    const proposalData: Proposal = res.ok
      ? (res.data as Proposal)
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
        };
    setProposal(proposalData);
    if (sessionId) persistSnapshot(sessionId, { proposal: proposalData });
    setConfirmText("");
  }

  async function runExecute() {
    if (!proposal?.proposal_id || killSwitchOn) return;
    if (!autonomous && confirmText.trim().toUpperCase() !== "CONFIRM") return;
    const res = await runAction("execute", { proposalId: proposal.proposal_id }, sessionId);
    const result: ExecutionResult | null = res.ok ? (res.data as ExecutionResult) : null;

    if (result?.executed && res.ok) {
      const record: TradeRecord = {
        id: result.order_id ?? crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        symbol: result.broker_symbol ?? proposal.broker_symbol ?? "",
        direction: result.direction ?? proposal.direction ?? "",
        size: result.size ?? proposal.size ?? 0,
        fill_price: result.fill_price,
        combined_signal: synthesis?.combined_signal ?? null,
      };
      const nextHistory = [record, ...history];
      persistHistory(nextHistory);
      setProposal(null);
      setConfirmText("");
      showToast(
        `Order filled — ${result.size ?? 0} ${(result.direction ?? "?").toUpperCase()} ${result.broker_symbol ?? ""} @ ${result.fill_price ?? "—"}`,
        "success",
      );
      if (sessionId) persistSnapshot(sessionId, { history: nextHistory, proposal: null });
      void runPositions();
    } else {
      const msg =
        (res.data as ExecutionResult | null)?.errors?.[0] ??
        res.error ??
        "The agent didn't confirm a fill.";
      showToast(msg, "error");
      const p = res.data as Proposal | null;
      if (p) {
        setProposal(p);
        if (sessionId) persistSnapshot(sessionId, { proposal: p });
      }
    }
  }

  async function runPositions() {
    const res = await runAction("positions", {}, sessionId);
    const pos = res.ok
      ? ((res.data as { positions?: Position[] } | null)?.positions ?? [])
      : [];
    setPositions(pos);
    if (sessionId && resolved) persistSnapshot(sessionId, { positions: pos });
  }

  function scrollTo(ref: RefObject<HTMLDivElement | null>) {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ------------------------------------------------------------------ */
  /* ------------------------------------------------------------------ */
  /* Derived visuals                                                     */
  /* ------------------------------------------------------------------ */
  liveRef.current = {
    symbol: resolved?.instrument_name ?? "",
    resolved,
    evidence,
    synthesis,
    proposal,
    positions,
    history,
    activity,
  };
  const d: SessionSnapshotData = viewing ? viewing.snapshot : liveRef.current;
  const exploringBusy = busy.explore && !viewing;

  const signalWord =
    d.synthesis?.combined_signal === "strong_long"
      ? "BULLISH"
      : d.synthesis?.combined_signal === "strong_short"
        ? "BEARISH"
        : d.synthesis?.combined_signal === "conflict_reduce"
          ? "MIXED"
          : d.synthesis?.combined_signal === "no_trade"
            ? "NO EDGE"
            : "—";

  const canTrade =
    d.synthesis?.combined_signal === "strong_long" ||
    d.synthesis?.combined_signal === "strong_short";
  const suggestedDirection: "buy" | "sell" =
    d.synthesis?.combined_signal === "strong_short" ? "sell" : "buy";

  const sentimentBar =
    d.evidence?.news?.sentiment_score != null
      ? Math.max(0, Math.min(100, (d.evidence.news.sentiment_score + 1) * 50))
      : 0;
  const rsiBar =
    d.evidence?.technical?.rsi != null
      ? Math.max(0, Math.min(100, d.evidence.technical.rsi))
      : 0;
  const confidenceBar =
    d.synthesis?.confidence === "high"
      ? 90
      : d.synthesis?.confidence === "medium"
        ? 58
        : d.synthesis?.confidence === "low"
          ? 28
          : 0;
  const riskBar =
    d.proposal?.risk_percent_used != null && preflight?.max_risk_percent
      ? Math.max(
          0,
          Math.min(
            100,
            (d.proposal.risk_percent_used / preflight.max_risk_percent) * 100,
          ),
        )
      : 0;

  const bars = [
    { label: "Sentiment", value: sentimentBar },
    { label: "RSI", value: rsiBar },
    { label: "Confidence", value: confidenceBar },
    { label: "Risk used", value: riskBar },
  ];

  const riskUsedPct = d.proposal?.risk_percent_used ?? 0;
  const riskMax = preflight?.max_risk_percent ?? 0;
  const riskArc =
    riskMax > 0 ? Math.max(0, Math.min(1, riskUsedPct / riskMax)) : 0;
  const riskCircumference = 2 * Math.PI * 40;

  const levels = d.evidence?.technical
    ? [
        d.evidence.technical.support,
        d.evidence.technical.suggested_stop_loss,
        d.evidence.technical.suggested_take_profit,
        d.evidence.technical.resistance,
      ].filter((v): v is number => v != null)
    : [];
  const levelMin = levels.length ? Math.min(...levels) : 0;
  const levelMax = levels.length ? Math.max(...levels) : 1;
  const pos = (v: number) =>
    levelMax === levelMin ? 50 : ((v - levelMin) / (levelMax - levelMin)) * 100;

  /* Sidebar connection glow — lit by real MCP servers the agent touched. */
  const activeServers = new Set<string>([
    ...connected,
    ...activity.tools.map((t) => t.server).filter((s): s is string => Boolean(s)),
  ]);
  const conn = (key: string) => activeServers.has(key);

  const snapshotIdle =
    sentimentBar === 0 && rsiBar === 0 && confidenceBar === 0 && riskBar === 0;

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

        {/* Sessions from the Neon archive */}
        <div className="relative mt-6 flex min-h-0 flex-col">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#8ea79b]">
              Sessions
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={startNewSession}
                title="Start a new exploration"
                className="rounded-full px-2 py-0.5 text-[10px] font-semibold text-[#8ea79b] transition hover:bg-white/10 hover:text-white"
              >
                new
              </button>
              <button
                onClick={() => void refreshSessions()}
                title="Refresh sessions"
                className="rounded-full p-1 text-[#8ea79b] transition hover:bg-white/10 hover:text-white"
              >
                <Ic name="refresh" className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <div className="flex max-h-[210px] flex-col gap-0.5 overflow-y-auto pr-1">
            {sessions.length === 0 ? (
              <p className="px-1 py-1 text-[11px] leading-relaxed text-[#8ea79b]">
                Completed explorations will appear here.
              </p>
            ) : (
              sessions.map((s) => {
                const isActive = (viewing?.id ?? sessionId) === s.id;
                return (
                  <div key={s.id} className="group flex items-center gap-1">
                    <button
                      onClick={() => void viewSession(s.id)}
                      className={`flex min-w-0 flex-1 items-center gap-2 rounded-xl px-3 py-2 text-left text-[12px] transition ${isActive ? "bg-[#f6f2e9] text-[#2c463f]" : "text-[#c3d3cb] hover:bg-white/5"}`}
                    >
                      <span className="min-w-0 truncate font-medium">
                        {s.title ?? `session · ${s.id.slice(0, 8)}`}
                      </span>
                      <span
                        className={`ml-auto shrink-0 text-[10px] ${isActive ? "text-[#8a978f]" : "text-[#7d9488]"}`}
                      >
                        {relativeTime(s.updatedAt)}
                      </span>
                    </button>
                    <button
                      onClick={() => void removeSession(s.id)}
                      title="Delete session"
                      className="rounded-lg p-1 text-[#7d9488] opacity-0 transition hover:text-[#c65b4e] group-hover:opacity-100"
                    >
                      <Ic name="x" className="h-3 w-3" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="relative mt-auto pt-8">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[#8ea79b]">
            Connections
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div
              title="MT5 — trader execution"
              className={`grid h-8 w-8 place-items-center rounded-full border-2 border-[#2c463f] text-[10px] font-bold text-white transition ${preflight?.bridge_alive ? "bg-[#3f9a8f]" : "bg-[#7a6b53]"} ${conn("trader") ? "ring-2 ring-[#e3a94d]/70" : ""}`}
            >
              MT5
            </div>
            <div
              title="News — news-scraper sentiment"
              className={`grid h-8 w-8 place-items-center rounded-full border-2 border-[#2c463f] text-[10px] font-bold text-[#2c463f] transition ${conn("news-scraper") ? "ring-2 ring-[#e3a94d]/70 bg-[#e3a94d]" : "bg-[#e3a94d]"}`}
            >
              NS
            </div>
            <div
              title="Technical — technical-analyst"
              className={`grid h-8 w-8 place-items-center rounded-full border-2 border-[#2c463f] text-[10px] font-bold text-white transition ${conn("technical-analyst") ? "bg-[#3f9a8f] ring-2 ring-[#e3a94d]/70" : "bg-[#3f9a8f]"}`}
            >
              TA
            </div>
            <span
              className={`ml-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${killSwitchOn ? "bg-[#c65b4e] text-white" : "bg-white/10 text-[#c3d3cb]"}`}
            >
              {killSwitchOn ? "kill on" : "live"}
            </span>
          </div>
          {activity.running && (
            <div className="mt-3 flex items-center gap-1.5 text-[10px] text-[#a9beb5]">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-[#3f9a8f]" />
              agent is working…
            </div>
          )}
        </div>
      </aside>

      {/* ---------------- MAIN ---------------- */}
      <main className="flex-1 overflow-y-auto px-8 py-7">
        {/* Explore bar */}
        <div className="mb-5 flex items-center gap-3 rounded-full bg-white px-3 py-2 shadow-[0_10px_30px_rgba(31,42,40,0.06)]">
          <Ic name="compass" className="ml-2 h-4 w-4 text-[#8a978f]" />
          <input
            ref={exploreRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runExplore()}
            placeholder="What do you want to explore today? Bitcoin, Apple, gold…"
            className="flex-1 bg-transparent text-sm text-[#20302c] placeholder-[#a3ada6] focus:outline-none"
          />
          {activity.running && (
            <span className="hidden items-center gap-1.5 text-xs font-medium text-[#2f7e72] sm:flex">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-[#3f9a8f]" />
              {activity.label ?? "working…"}
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
          <p className="-mt-3 mb-5 flex items-center gap-1.5 text-xs text-[#c65b4e]">
            <Ic name="alert" className="h-3.5 w-3.5" /> {exploreError}
          </p>
        )}

        {viewing && (
          <div className="mb-5 flex items-center justify-between gap-3 rounded-full border border-[#e3a94d]/40 bg-[#e3a94d]/15 px-4 py-2.5 text-xs text-[#5c4a20]">
            <span className="flex min-w-0 items-center gap-2">
              <Ic name="stack" className="h-4 w-4 shrink-0" />
              <span className="truncate">
                Showing saved session{" "}
                <b className="font-semibold">
                  {viewing.snapshot.symbol || viewing.id.slice(0, 8)}
                </b>
              </span>
            </span>
            <button
              onClick={resumeLive}
              className="shrink-0 rounded-full bg-[#2c463f] px-3 py-1 font-semibold text-white transition hover:bg-[#20342f]"
            >
              Resume live
            </button>
          </div>
        )}

        {/* Live agent process feed */}
        <div className="mb-5">
          <AgentActivity
            activity={d.activity}
            onClear={clearActivity}
            onToggle={toggleActivity}
          />
        </div>

        {/* Hero row */}
        <div
          ref={heroRef}
          className="mb-5 grid grid-cols-1 gap-5 md:grid-cols-3"
        >
          <div className="rounded-[28px] bg-[#e3a94d] p-6 text-[#3a2c10]">
            <div className="mb-8 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide opacity-70">
                Today&apos;s read
              </span>
              <Ic
                name={
                  synthesis?.combined_signal === "strong_short" ? "down" : "up"
                }
                className="h-5 w-5 opacity-70"
              />
            </div>
            {exploringBusy && !d.resolved ? (
              <div className="space-y-2">
                <Skeleton className="h-6 w-24 opacity-40" />
                <Skeleton className="h-3 w-16 opacity-40" />
              </div>
            ) : (
              <>
                <div className="text-2xl font-extrabold">
                  {d.resolved?.instrument_name ?? "—"}
                </div>
                <div className="mt-1 text-sm font-semibold opacity-80">
                  {signalWord}
                </div>
              </>
            )}
          </div>

          <div className="rounded-[28px] bg-[#3f9a8f] p-6 text-white">
            <div className="mb-8 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide opacity-80">
                Confidence
              </span>
              <Ic name="shield" className="h-5 w-5 opacity-80" />
            </div>
            {exploringBusy && !d.synthesis ? (
              <div className="space-y-2">
                <Skeleton className="h-6 w-24 bg-white/25" />
                <Skeleton className="h-3 w-20 bg-white/25" />
              </div>
            ) : (
              <>
                <div className="text-2xl font-extrabold capitalize">
                  {d.synthesis?.confidence ?? "—"}
                </div>
                <div className="mt-1 text-sm opacity-80">
                  {d.evidence?.news?.sentiment_trend
                    ? `sentiment ${d.evidence.news.sentiment_trend}`
                    : "awaiting a read"}
                </div>
              </>
            )}
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
            {busy.positions && !viewing && d.positions.length === 0 ? (
              <div className="relative flex items-center gap-2">
                <Skeleton className="h-6 w-8" />
                <Skeleton className="h-3 w-20" />
              </div>
            ) : (
              <>
                <div className="relative text-2xl font-extrabold text-[#20302c]">
                  {d.positions.length}
                </div>
                <div className="relative mt-1 text-sm text-[#8a978f]">
                  {preflight?.account
                    ? `equity $${preflight.account.equity.toLocaleString()}`
                    : "checking account…"}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Trade pill / hold-off note, tied to the synthesis */}
        {d.synthesis && (
          <div className="animate-fade-up mb-5 flex flex-wrap items-center gap-3 rounded-[24px] bg-white px-6 py-4 shadow-[0_10px_30px_rgba(31,42,40,0.06)]">
            <p className="flex-1 text-sm text-[#4a5751]">
              {d.synthesis.rationale}
            </p>
            {killSwitchOn ? (
              <span className="rounded-full bg-[#f3e2df] px-4 py-2 text-xs font-semibold text-[#c65b4e]">
                kill switch is on — no trading right now
              </span>
            ) : canTrade ? (
              <button
                onClick={() => !viewing && runPropose(suggestedDirection)}
                disabled={Boolean(viewing) || busy.propose}
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
        {d.proposal && (
          <div className="mb-5 flex flex-wrap items-center gap-3 rounded-[24px] border border-[#e3a94d]/40 bg-[#fdf6e8] px-6 py-4">
            <div className="flex-1 text-sm text-[#5c4a20]">
              <span className="font-semibold">{d.proposal.broker_symbol}</span> ·{" "}
              {d.proposal.direction} · {d.proposal.size} lots · SL{" "}
              {d.proposal.stop_loss} / TP {d.proposal.take_profit}
            </div>
            {d.proposal.errors?.length > 0 && (
              <span className="text-xs text-[#c65b4e]">
                {d.proposal.errors[0]}
              </span>
            )}
            {!viewing && !autonomous && (
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
              onClick={!viewing ? runExecute : undefined}
              disabled={
                Boolean(viewing) ||
                busy.execute ||
                (!autonomous && confirmText.trim().toUpperCase() !== "CONFIRM")
              }
              className="rounded-full bg-[#2c463f] px-4 py-1.5 text-xs font-semibold text-white disabled:opacity-30"
            >
              {busy.execute ? "sending…" : "Execute"}
            </button>
            <button
              onClick={() => !viewing && setProposal(null)}
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
                d.history.length === 0 ? (
                  <p className="py-6 text-center text-sm text-[#8a978f]">
                    No trades yet — explore something above and take the call
                    when it looks right.
                  </p>
                ) : (
                  <div className="space-y-1">
                    {d.history.slice(0, 6).map((t) => (
                      <div
                        key={t.id}
                        className="animate-slide-in-right flex items-center gap-3 rounded-2xl px-2 py-2.5 hover:bg-[#f6f2e9]"
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
              ) : d.positions.length === 0 ? (
                <p className="py-6 text-center text-sm text-[#8a978f]">
                  Nothing open right now.
                </p>
              ) : (
                <div className="space-y-1">
                  {d.positions.map((p) => (
                    <div
                      key={p.broker_symbol}
                      className="animate-slide-in-right flex items-center gap-3 rounded-2xl px-2 py-2.5 hover:bg-[#f6f2e9]"
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
                        className={`text-sm font-semibold transition-colors ${p.pnl >= 0 ? "text-[#3f9a8f]" : "text-[#c65b4e]"}`}
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
            {exploringBusy && snapshotIdle ? (
              <div className="flex h-40 items-end justify-between gap-3">
                {[0, 1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="flex flex-1 flex-col items-center gap-2"
                  >
                    <div className="flex h-32 w-full items-end overflow-hidden rounded-full bg-[#f2efe6]">
                      <Skeleton className="h-24 w-full rounded-full" />
                    </div>
                    <Skeleton className="h-2 w-10" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex h-40 items-end justify-between gap-3">
                {bars.map((b, i) => (
                  <div
                    key={b.label}
                    className="flex flex-1 flex-col items-center gap-2"
                  >
                    <div className="flex h-32 w-full items-end overflow-hidden rounded-full bg-[#f2efe6]">
                      <div
                        className="bar-animate w-full rounded-full bg-[#3f9a8f] transition-[height] duration-500"
                        style={{
                          height: `${b.value}%`,
                          animationDelay: `${i * 60}ms`,
                        }}
                      />
                    </div>
                    <span className="text-center text-[10px] leading-tight text-[#8a978f]">
                      {b.label}
                    </span>
                  </div>
                ))}
              </div>
            )}
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
                  style={{
                    transition:
                      "stroke-dashoffset 700ms cubic-bezier(0.16,1,0.3,1)",
                  }}
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
                d.evidence
                  ? `${d.evidence.ta_symbol} · support to resistance`
                  : "Explore a symbol to see this"
              }
            >
              {exploringBusy && !d.evidence ? (
                <div className="space-y-3 py-4">
                  <Skeleton className="mx-auto h-5 w-32" />
                  <Skeleton className="h-1.5 w-full" />
                </div>
              ) : levels.length >= 2 ? (
                <div className="relative mt-6 pb-6">
                  {d.evidence?.technical?.verdict && (
                    <div className="absolute -top-2 left-1/2 -translate-x-1/2 rounded-full bg-[#2c463f] px-3 py-1 text-[11px] font-semibold text-white">
                      {d.evidence.technical.verdict} verdict
                    </div>
                  )}
                  <div className="relative mt-10 h-1.5 rounded-full bg-[#f2efe6]">
                    <div
                      className="absolute inset-y-0 rounded-full bg-gradient-to-r from-[#c65b4e] via-[#e3a94d] to-[#3f9a8f]"
                      style={{ left: 0, right: 0 }}
                    />
                    {d.evidence?.technical?.support != null && (
                      <div
                        className="animate-fade-up absolute -top-7 flex -translate-x-1/2 flex-col items-center text-[10px] text-[#8a978f]"
                        style={{ left: `${pos(d.evidence.technical.support)}%` }}
                      >
                        <span>support</span>
                        <span className="font-semibold text-[#20302c]">
                          {d.evidence.technical.support}
                        </span>
                      </div>
                    )}
                    {d.evidence?.technical?.suggested_stop_loss != null && (
                      <div
                        className="absolute -bottom-7 flex -translate-x-1/2 flex-col items-center text-[10px] text-[#8a978f]"
                        style={{
                          left: `${pos(d.evidence.technical.suggested_stop_loss)}%`,
                        }}
                      >
                        <span className="font-semibold text-[#c65b4e]">
                          {d.evidence.technical.suggested_stop_loss}
                        </span>
                        <span>stop</span>
                      </div>
                    )}
                    {d.evidence?.technical?.suggested_take_profit != null && (
                      <div
                        className="absolute -bottom-7 flex -translate-x-1/2 flex-col items-center text-[10px] text-[#8a978f]"
                        style={{
                          left: `${pos(d.evidence.technical.suggested_take_profit)}%`,
                        }}
                      >
                        <span className="font-semibold text-[#3f9a8f]">
                          {d.evidence.technical.suggested_take_profit}
                        </span>
                        <span>target</span>
                      </div>
                    )}
                    {d.evidence?.technical?.resistance != null && (
                      <div
                        className="absolute -top-7 flex -translate-x-1/2 flex-col items-center text-[10px] text-[#8a978f]"
                        style={{
                          left: `${pos(d.evidence.technical.resistance)}%`,
                        }}
                      >
                        <span>resistance</span>
                        <span className="font-semibold text-[#20302c]">
                          {d.evidence.technical.resistance}
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

      {/* Toast */}
      {toast && (
        <div key={toast.id} className="fixed bottom-6 right-6 z-50 animate-fade-up">
          <div
            className={`flex max-w-sm items-center gap-2.5 rounded-2xl px-4 py-3 text-sm font-medium text-white shadow-[0_10px_30px_rgba(31,42,40,0.25)] ${toast.tone === "success" ? "bg-[#2f7e72]" : toast.tone === "error" ? "bg-[#b34e42]" : "bg-[#2c463f]"}`}
          >
            <Ic
              name={
                toast.tone === "success"
                  ? "check"
                  : toast.tone === "error"
                    ? "alert"
                    : "signal"
              }
              className="h-4 w-4 shrink-0"
            />
            <span className="min-w-0">{toast.message}</span>
          </div>
        </div>
      )}
    </div>
  );
}