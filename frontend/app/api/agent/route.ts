// app/api/agent/route.ts
//
// ACTION-based endpoint that streams the TrueForge agent's live work back to
// the browser as Server-Sent Events. Each dashboard section POSTs
// { action, params, sessionId } and receives an event stream:
//
//   session.id   -> the (created or reused) session id
//   action       -> phase metadata for the requested action
//   connecting   -> MCP servers the agent initialised (list)
//   text         -> incremental assistant message content
//   reason       -> incremental model reasoning content
//   tool.start   -> a tool call began (name + MCP server when known)
//   tool.args    -> incremental tool arguments payload
//   tool.done    -> a tool call finished (output preview)
//   done         -> terminal { ok, data, raw } with the parsed JSON result
//   error        -> terminal failure
//
// AUTHORITY & AUTH: trueforge.saastralabs.com sits behind a host-level HTTP
// Basic Auth prompt, so credentials are injected server-side here when the
// SDK client is built. Never surface them to the browser.

import { TrueForge } from "@truefoundry/trueforge-sdk";
import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const username = "admin";
const password = "admin";

const basicAuth = Buffer.from(`${username}:${password}`).toString("base64");

const client = new TrueForge({
  baseUrl: "https://trueforge.saastralabs.com",
  headers: { Authorization: `Basic ${basicAuth}` },
  timeoutInSeconds: 600,
});

type ActionName =
  | "preflight"
  | "resolve_formats"
  | "evidence"
  | "synthesize"
  | "propose"
  | "execute"
  | "positions"
  | "close_position";

interface PhaseMeta {
  label: string;
  hint: string;
  step: number;
}

/** Pipeline position of each action so the UI can render a stepper. */
const PHASES: Record<ActionName, PhaseMeta> = {
  preflight: { label: "Pre-flight", hint: "Safety config & account read", step: 0 },
  resolve_formats: { label: "Resolve", hint: "Map the query to the right symbol formats", step: 1 },
  evidence: { label: "Gather evidence", hint: "News sentiment + technical read", step: 2 },
  synthesize: { label: "Decide", hint: "Weigh the evidence into a call", step: 3 },
  propose: { label: "Size & guard", hint: "Check safety guards & stage the trade", step: 4 },
  execute: { label: "Execute", hint: "Send the order to MT5", step: 5 },
  positions: { label: "Positions", hint: "Open positions from MT5", step: 6 },
  close_position: { label: "Close", hint: "Confirm the close is warranted", step: 6 },
};

/**
 * Hard contract every action prompt ends with. The model is told to emit the
 * JSON schema as its LAST message and nothing else — and even if it doesn't,
 * extractLastJson (below) still pulls the last well-formed object out of the
 * accumulated text, so the UI always receives the definite shape it asked for.
 */
const JSON_ONLY_SUFFIX = `
You must finish the turn with EXACTLY ONE JSON object matching the schema
above. Rules:
- It is your LAST output. Do not stream commentary before, between, or after.
- No Markdown, no code fences, no trailing prose, no closing remarks.
- Emit every key from the schema. For any value you could not obtain from a
  tool call or the provided context, set it to null and add a short human
  explanation to the "errors" array.
- Only report numbers you actually received from a tool. Never invent, round
  creatively, or estimate a value you do not have.`;

/** Extract the final complete JSON object from a concatenated stream. */
function extractLastJson(text: string): unknown | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    /* fall through to brace matching */
  }

  let start = trimmed.lastIndexOf("{");
  if (start === -1) start = trimmed.lastIndexOf("[");
  if (start === -1) return null;

  const open = trimmed[start];
  const close = open === "{" ? "}" : "]";
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let i = start; i < trimmed.length; i++) {
    const c = trimmed[i];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (c === "\\") {
      escaped = true;
      continue;
    }
    if (c === '"') {
      inString = !inString;
      continue;
    }
    if (inString) continue;
    if (c === open) depth++;
    else if (c === close) {
      depth--;
      if (depth === 0) {
        try {
          return JSON.parse(trimmed.slice(start, i + 1));
        } catch {
          return null;
        }
      }
    }
  }
  try {
    return JSON.parse(trimmed.slice(start));
  } catch {
    return null;
  }
}

/** Heuristic server label for a tool name (the MCP server it belongs to). */
function serverOf(toolName: string): string | undefined {
  const dot = toolName.indexOf(".");
  if (dot > 0) return toolName.slice(0, dot);
  return undefined;
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

function buildPrompt(action: ActionName, params: Record<string, unknown>): string {
  switch (action) {
    case "preflight":
      return `Run ONLY Phase 0 (pre-flight): trader.ping,
trader.get_safety_config, trader.get_account_info. Do not resolve any symbol
and do not call propose_trade or execute_trade.
Return JSON:
{"bridge_alive":boolean,"kill_switch_on":boolean,"max_risk_percent":number,
"position_caps":string,"account":{"balance":number,"equity":number,
"margin":number,"leverage":number},"errors":string[]}${JSON_ONLY_SUFFIX}`;

    case "resolve_formats":
      return `Run ONLY Phase 1 for the instrument named "${params.query}".
Do NOT call trader.resolve_symbol — that is out of scope until Phase 4.
Derive: (a) the news-scrape format — bare ticker, no suffix, e.g. "BTC",
"AAPL", "XAU"; (b) the technical-analyst format — yfinance-style ticker,
e.g. "BTC-USD", "AAPL", "XAUUSD=X", "EURUSD=X". These are often different
strings for the same instrument — do not assume they match.
Return JSON:
{"input":string,"instrument_name":string,"news_symbol":string,
"ta_symbol":string,"errors":string[]}${JSON_ONLY_SUFFIX}`;

    case "evidence":
      return `Run ONLY Phase 2. Use news_symbol "${params.newsSymbol}" for the
news leg (get_news, scrape_news+poll get_job_status only if stale/empty,
get_sentiment_summary, get_sentiment_trend, get_source_comparison) and
ta_symbol "${params.taSymbol}" for the technical leg
(get_technical_analysis, get_analysis_history). Never send ta_symbol to
news-scrape or news_symbol to technical-analyst — if a leg errors with
symbol-not-found, double check you used the right one before reporting a
data gap. Run both legs; if one fails, say so in "errors" and continue with
the other. Do not synthesize a decision here.
Return JSON:
{"news_symbol":string,"ta_symbol":string,
"news":{"sentiment_score":number,"sentiment_label":string,
"sentiment_trend":string,"source_divergence":string,"headline_count":number,
"top_headlines":string[]},
"technical":{"trend":string,"rsi":number,"macd_signal":string,
"volatility_atr":number,"support":number,"resistance":number,
"verdict":string,"verdict_stability":string,"suggested_stop_loss":number,
"suggested_take_profit":number},
"errors":string[]}${JSON_ONLY_SUFFIX}`;

    case "synthesize":
      return `Run ONLY Phase 3 for this instrument. Evidence already
gathered this session (do not re-fetch unless a field is null):
${JSON.stringify(params.evidence)}
Apply the playbook's decision table: agreement between legs raises
confidence; disagreement shrinks size or vetoes; wide source divergence
lowers confidence; a verdict that just flipped is provisional. "No trade" is
a valid output — never force a rationale to justify a trade.
Return JSON:
{"combined_signal":"strong_long"|"strong_short"|"conflict_reduce"|"no_trade",
"confidence":"high"|"medium"|"low","rationale":string,
"recommended_size_note":string,"errors":string[]}${JSON_ONLY_SUFFIX}`;

    case "propose":
      return `Run Phase 4 steps 0-4 (propose only, do NOT execute) for the
instrument named "${params.instrumentName}", direction "${params.direction}".
Step 0: call trader.resolve_symbol on "${params.instrumentName}" to get the
broker-suffixed symbol (e.g. "BTCUSDm") — this is the first point this
symbol format is needed. Then re-check trader.get_safety_config. Compute
size from account equity x max risk % and the ATR-based stop from this
evidence/synthesis:
${JSON.stringify({ evidence: params.evidence, synthesis: params.synthesis })}
Do not exceed the configured max risk % or position cap. If kill switch is
on or size would exceed the cap, do not call propose_trade — explain why in
"errors" instead. Otherwise call trader.propose_trade with the resolved
broker symbol, then trader.get_proposal to confirm what was recorded.
Return JSON:
{"proposal_id":string,"direction":string,"broker_symbol":string,
"size":number,"stop_loss":number,"take_profit":number,
"risk_percent_used":number,"kill_switch_on":boolean,
"within_position_cap":boolean,"expires_at":string,
"errors":string[]}${JSON_ONLY_SUFFIX}`;

    case "execute":
      return `Run ONLY Phase 4 step 6: execute the confirmed proposal id
"${params.proposalId}" via trader.execute_trade, referencing that proposal
id. If it has expired, do not force execution — report that in "errors"
and do not fabricate a fill.
Return JSON:
{"executed":boolean,"order_id":string,"fill_price":number,
"broker_symbol":string,"direction":string,"size":number,
"account_after":{"balance":number,"equity":number,"margin":number},
"errors":string[]}${JSON_ONLY_SUFFIX}`;

    case "positions":
      return `Call trader.get_positions and return open positions only. Do
not modify anything.
Return JSON:
{"positions":[{"broker_symbol":string,"direction":string,"size":number,
"entry_price":number,"current_price":number,"pnl":number,
"stop_loss":number,"take_profit":number}],"errors":string[]}${JSON_ONLY_SUFFIX}`;

    case "close_position":
      return `Re-run Phase 2's technical leg using ta_symbol
"${params.taSymbol}" to confirm the close is warranted, then call
trader.close_position for broker symbol "${params.brokerSymbol}".
Return JSON:
{"closed":boolean,"broker_symbol":string,"close_price":number,"pnl":number,
"errors":string[]}${JSON_ONLY_SUFFIX}`;

    default:
      throw new Error(`Unknown action: ${action}`);
  }
}

interface ToolFeed {
  index: number;
  id?: string;
  name: string;
  server?: string;
  argsFragments: string[];
  started: boolean;
}

async function runAction(
  sessionId: string,
  action: ActionName,
  params: Record<string, unknown>,
  send: (payload: Record<string, unknown>) => void,
): Promise<void> {
  const prompt = buildPrompt(action, params);
  send({ type: "action", action, label: PHASES[action].label, hint: PHASES[action].hint });

  const stream = await client.sessions.createTurnStream(sessionId, {
    input: [{ type: "user.message", content: prompt }],
  });

  const tools = new Map<number, ToolFeed>();
  let buf = "";

  for await (const { data: event } of stream.withMetadata()) {
    switch (event.type) {
      case "mcp.initialize": {
        const servers = (event.mcpServers ?? []).map((s) => s.name).filter(Boolean);
        if (servers.length) send({ type: "connecting", servers });
        break;
      }

      case "model.message.delta": {
        if (event.content) {
          buf += event.content;
          send({ type: "text", text: event.content });
        }
        if (event.reasoningContent) {
          send({ type: "reason", text: event.reasoningContent });
        }
        for (const tc of event.toolCalls ?? []) {
          const entry = tools.get(tc.index) ?? {
            index: tc.index,
            name: "",
            argsFragments: [],
            started: false,
          };
          if (tc.id) entry.id = tc.id;
          if (tc.function?.name) entry.name += tc.function.name;
          if (tc.function?.arguments) entry.argsFragments.push(tc.function.arguments);
          tools.set(tc.index, entry);
          if (!entry.started && entry.name.length >= 2) {
            entry.started = true;
            const server = serverOf(entry.name);
            send({
              type: "tool.start",
              index: entry.index,
              id: entry.id,
              name: entry.name,
              server,
            });
          }
          const args = entry.argsFragments.join("");
          send({ type: "tool.args", index: entry.index, args: truncate(args, 4000) });
        }
        break;
      }

      case "model.message": {
        const content = typeof event.content === "string" ? event.content : null;
        if (content) {
          buf += content;
          send({ type: "text", text: content });
        }
        if (event.reasoningContent) {
          send({ type: "reason", text: event.reasoningContent });
        }
        for (const tc of event.toolCalls ?? []) {
          if (!tc.id || !tc.function?.name) continue;
          const entry: ToolFeed = {
            index: tools.size,
            id: tc.id,
            name: tc.function.name,
            argsFragments: tc.function.arguments ? [tc.function.arguments] : [],
            started: true,
          };
          tools.set(entry.index, entry);
          send({
            type: "tool.start",
            index: entry.index,
            id: tc.id,
            name: tc.function.name,
            server: serverOf(tc.function.name),
          });
        }
        break;
      }

      case "tool.response": {
        send({
          type: "tool.done",
          toolCallId: event.toolCallId,
          content: truncate(event.content ?? "", 1400),
        });
        break;
      }

      case "turn.done":
      case "thread.done":
        break;
    }

    if (event.type === "turn.done") break;
  }

  const data = extractLastJson(buf);
  if (data === null) {
    send({
      type: "error",
      error: "Agent did not return valid JSON for this action.",
      raw: truncate(buf, 2000),
    });
    return;
  }
  send({ type: "done", ok: true, data, raw: truncate(buf, 4000) });
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body.action !== "string") {
    return new Response(JSON.stringify({ error: "action is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const action = body.action as ActionName;
  const params = body.params ?? {};
  let sid = body.sessionId as string | undefined;

  const encoder = new TextEncoder();

  const send = (payload: Record<string, unknown>) => {
    controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
  };

  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const stream = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c;
    },
  });

  void (async () => {
    const heartbeat = setInterval(() => {
      try {
        controller.enqueue(encoder.encode(": ping\n\n"));
      } catch {
        /* stream closed */
      }
    }, 15_000);
    try {
      if (!sid) {
        const { data: session } = await client.sessions.create({
          agent: { name: "trading-agent" },
        });
        sid = session.id;
      }
      send({ type: "session.id", sessionId: sid });
      await runAction(sid, action, params, send);
    } catch (err) {
      send({
        type: "error",
        error: String(err instanceof Error ? err.message : err),
      });
    } finally {
      clearInterval(heartbeat);
      try {
        controller.close();
      } catch {
        /* already closed */
      }
    }
  })();

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}