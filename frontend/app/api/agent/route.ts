// app/api/agent/route.ts
//
// This replaces the old chat-style streaming route with an ACTION-based route.
// Each dashboard section calls this with { action, params, sessionId } and gets
// back ONE parsed JSON object — no chat, no streamed deltas to the browser.
//
// IMPORTANT — auth fix:
// trueforge.saastralabs.com sits behind an HTTP Basic Auth prompt at the host
// level (the browser-native "Sign in" dialog — that's Basic Auth, not
// TrueForge's own OIDC login page). The browser can't complete that from a
// fetch() call in the dashboard, so it has to be injected server-side, here,
// when the SDK client is constructed.
//
// @truefoundry/trueforge-sdk is Stainless-generated, so it should accept
// `defaultHeaders` in its constructor. If your installed version doesn't,
// swap the `defaultHeaders` line for a custom `fetch` wrapper passed as
// `fetcher` / `httpClient` (check node_modules/@truefoundry/trueforge-sdk's
// Client type for the exact option name in your version).

import { TrueForge } from "@truefoundry/trueforge-sdk";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const username = "admin";
const password = "admin";

const basicAuth = Buffer.from(`${username}:${password}`).toString("base64");

const client = new TrueForge({
  baseUrl: "https://trueforge.saastralabs.com",

  headers: {
    Authorization: `Basic ${basicAuth}`,
  },

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

const JSON_ONLY_SUFFIX = `
Respond with ONLY a single valid JSON object matching the schema above.
No markdown code fences, no prose before or after. If a tool call fails or a
value is unavailable, keep the key and set it to null, and add a short
description to the "errors" array. Never invent or estimate a number you did
not get from a tool.`;

function buildPrompt(action: ActionName, params: Record<string, any>): string {
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

async function runAction(
  sessionId: string,
  action: ActionName,
  params: Record<string, any>,
) {
  const prompt = buildPrompt(action, params);
  const stream = await client.sessions.createTurnStream(sessionId, {
    input: [{ type: "user.message", content: prompt }],
  });

  let full = "";
  for await (const { data: event } of stream.withMetadata()) {
    if (event.type === "model.message.delta" && event.content)
      full += event.content;
    if (event.type === "turn.done") break;
  }

  const cleaned = full
    .trim()
    .replace(/^```json\s*|^```\s*|```$/g, "")
    .trim();
  try {
    return { ok: true as const, data: JSON.parse(cleaned), raw: full };
  } catch {
    return {
      ok: false as const,
      data: null,
      raw: full,
      error: "Agent did not return valid JSON for this action.",
    };
  }
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body.action !== "string") {
    return NextResponse.json({ error: "action is required" }, { status: 400 });
  }

  const action = body.action as ActionName;
  const params = body.params ?? {};
  let sid = body.sessionId as string | undefined;

  try {
    if (!sid) {
      const { data: session } = await client.sessions.create({
        agent: { name: "trading-agent" },
      });
      sid = session.id;
    }
    const result = await runAction(sid, action, params);
    return NextResponse.json({ sessionId: sid, action, ...result });
  } catch (err) {
    return NextResponse.json(
      { sessionId: sid, action, ok: false, error: String(err) },
      { status: 502 },
    );
  }
}
