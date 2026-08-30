// Client-side reader for the streaming /api/agent endpoint.

export type AgentEvent =
  | { type: "session.id"; sessionId: string }
  | { type: "action"; action: string; label: string; hint: string }
  | { type: "connecting"; servers: string[] }
  | { type: "text"; text: string }
  | { type: "reason"; text: string }
  | {
      type: "tool.start";
      index: number;
      id?: string;
      name: string;
      server?: string;
    }
  | { type: "tool.args"; index: number; args: string }
  | { type: "tool.done"; toolCallId: string; content: string }
  | { type: "done"; ok: boolean; data: unknown; raw?: string }
  | { type: "error"; error: string; raw?: string };

export interface StreamResult {
  sessionId: string;
  ok: boolean;
  data: unknown;
  raw?: string;
  error?: string;
}

export interface ToolState {
  index: number;
  id?: string;
  name: string;
  server?: string;
  status: "started" | "done";
  args?: string;
  content?: string;
}

export interface ActivityLogEntry {
  kind: "info" | "tool" | "text" | "reason" | "error";
  message: string;
}

export interface ActivityState {
  running: boolean;
  action?: string;
  label?: string;
  hint?: string;
  step: number;
  tools: ToolState[];
  text: string;
  reason: string;
  log: ActivityLogEntry[];
  error?: string;
  expanded?: boolean;
}

function parseSseChunk(chunk: string): Record<string, unknown> | null {
  let data = "";
  for (const line of chunk.split("\n")) {
    if (line.startsWith("data:")) data += line.slice(5).trimStart();
  }
  if (!data.trim()) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

/**
 * POST an action and read the SSE stream, invoking `onEvent` for every
 * normalized event. Resolves once the terminal `done`/`error` event arrives.
 */
export async function streamAgent(
  action: string,
  params: Record<string, unknown>,
  sessionId: string | null,
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<StreamResult> {
  const res = await fetch("/api/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, params, sessionId }),
    signal,
  });

  if (!res.ok || !res.body) {
    let message = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      if (json?.error) message = json.error;
    } catch {
      /* keep the HTTP fallback */
    }
    throw new Error(message);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let sid = sessionId ?? "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const payload = parseSseChunk(block);
        if (!payload) continue;
        const event = payload as unknown as AgentEvent;
        if (event.type === "session.id") sid = event.sessionId;
        onEvent(event);
        if (event.type === "done" || event.type === "error") {
          if (event.type === "done") {
            return { sessionId: sid, ok: event.ok, data: event.data, raw: event.raw };
          }
          return { sessionId: sid, ok: false, data: null, error: event.error, raw: event.raw };
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  return {
    sessionId: sid,
    ok: false,
    data: null,
    error: "Stream ended without a final event.",
  };
}