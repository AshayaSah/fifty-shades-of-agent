"use client";

import { useState } from "react";
import type { ReactNode } from "react";

import type { ActivityState, ToolState } from "@/lib/agent";

/* Palette-matched server tints (trader teal / news gold / technical dark). */
const SERVER_TINT: Record<string, { bg: string; text: string }> = {
  trader: { bg: "#e2f0ec", text: "#2f7e72" },
  "news-scraper": { bg: "#f7ecd2", text: "#9a7617" },
  "technical-analyst": { bg: "#e6ebe8", text: "#2c463f" },
};

function tintFor(server?: string) {
  return (server && SERVER_TINT[server]) || { bg: "#f2efe6", text: "#5c6b64" };
}

function serverLabel(server?: string) {
  if (server === "trader") return "MT5";
  if (server === "news-scraper") return "News";
  if (server === "technical-analyst") return "Technical";
  return server ?? "agent";
}

function Ic({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  const paths: Record<string, ReactNode> = {
    zap: <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />,
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
    activity: <path d="M3 12h4l3-9 5 18 3-9h3" />,
    chevron: <path d="m9 6 6 6-6 6" />,
    eraser: (
      <>
        <path d="M7 20h13" />
        <path d="M3 12l6-6 9 9-6 6a2 2 0 0 1-1.5.6L8 14h4l-6-6-4.5 4.5a2 2 0 0 0-.5 1.2V17l6 6" />
      </>
    ),
  };
  return (
    <svg viewBox="0 0 24 24" className={className} {...common}>
      {paths[name] ?? null}
    </svg>
  );
}

function StatusDot({ running }: { running: boolean }) {
  if (running) {
    return (
      <span className="relative grid h-2.5 w-2.5 place-items-center">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#3f9a8f] opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-[#3f9a8f]" />
      </span>
    );
  }
  return <span className="inline-flex h-2 w-2 rounded-full bg-[#8a978f]" />;
}

function ToolChip({ tool }: { tool: ToolState }) {
  const tint = tintFor(tool.server);
  const [open, setOpen] = useState(false);
  const hasDetail = Boolean(tool.args || tool.content);
  return (
    <div
      className="animate-scale-in rounded-full border"
      style={{ borderColor: tint.bg, background: tint.bg }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-left text-[11px]"
      >
        {tool.status === "started" ? (
          <Ic name="zap" className="h-3 w-3 animate-pulse-soft" />
        ) : (
          <Ic name="check" className="h-3 w-3" />
        )}
        <span
          className="rounded px-1 py-0.5 text-[9px] font-semibold uppercase tracking-wider"
          style={{ color: tint.text }}
        >
          {serverLabel(tool.server)}
        </span>
        <span className="font-mono text-[#20302c]">{tool.name}</span>
        {hasDetail && (
          <Ic
            name="chevron"
            className={`h-3 w-3 text-[#8a978f] transition-transform ${open ? "rotate-90" : ""}`}
          />
        )}
      </button>
      {open && hasDetail && (
        <div
          className="tool-feed border-t px-3 py-2"
          style={{ borderColor: tint.bg }}
        >
          {tool.args && (
            <>
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[#8a978f]">
                args
              </div>
              <pre className="text-[10px] leading-relaxed text-[#4a5751]">
                {tool.args}
              </pre>
            </>
          )}
          {tool.content !== undefined && (
            <>
              <div className="mt-2 mb-1 text-[10px] font-semibold uppercase tracking-wider text-[#8a978f]">
                result
              </div>
              <pre className="text-[10px] leading-relaxed text-[#4a5751]">
                {tool.content}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}

const FLOW: { step: number; label: string }[] = [
  { step: 1, label: "Resolve" },
  { step: 2, label: "Evidence" },
  { step: 3, label: "Decide" },
  { step: 4, label: "Size" },
  { step: 5, label: "Execute" },
];

const LOG_ICON: Record<string, string> = {
  info: "signal",
  tool: "activity",
  text: "activity",
  reason: "signal",
  error: "alert",
};

export default function AgentActivity({
  activity,
  onClear,
  onToggle,
}: {
  activity: ActivityState;
  onClear: () => void;
  onToggle: () => void;
}) {
  const [showAll, setShowAll] = useState(false);

  const hasWork = activity.log.length > 0 || activity.running;
  const inChain = activity.step >= 1 && activity.step <= 5;
  const visibleLog = showAll ? activity.log : activity.log.slice(-5);
  const expanded = activity.expanded !== false;

  return (
    <section className="animate-fade-up rounded-[28px] bg-white p-5 shadow-[0_10px_30px_rgba(31,42,40,0.06)]">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h3 className="text-[15px] font-bold text-[#20302c]">Agent activity</h3>
          {activity.running ? (
            <span className="flex items-center gap-1.5 rounded-full bg-[#e2f0ec] px-2.5 py-1 text-[10px] font-semibold text-[#2f7e72]">
              <StatusDot running /> working
            </span>
          ) : activity.error ? (
            <span className="rounded-full bg-[#f3e2df] px-2.5 py-1 text-[10px] font-semibold text-[#c65b4e]">
              failed
            </span>
          ) : hasWork ? (
            <span className="rounded-full bg-[#f2efe6] px-2.5 py-1 text-[10px] font-semibold text-[#8a978f]">
              done
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-1">
          {hasWork && (
            <button
              onClick={onClear}
              className="flex items-center gap-1 rounded-full px-2 py-1 text-[11px] text-[#8a978f] transition hover:bg-[#f6f2e9] hover:text-[#20302c]"
            >
              <Ic name="eraser" className="h-3 w-3" />
              clear
            </button>
          )}
          <button
            onClick={onToggle}
            className="rounded-full p-1.5 text-[#8a978f] transition hover:bg-[#f6f2e9]"
            aria-label="Toggle agent activity"
          >
            <Ic
              name="chevron"
              className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-90" : ""}`}
            />
          </button>
        </div>
      </header>

      {!hasWork ? (
        <div className="flex items-center gap-3 rounded-2xl bg-[#f6f2e9] px-4 py-3 text-sm text-[#8a978f]">
          <Ic name="signal" className="h-4 w-4 shrink-0" />
          <span>
            Explore a symbol and you&apos;ll see every step here — which server the
            agent calls, what it sees, and the verdict it lands on.
          </span>
        </div>
      ) : null}

      {hasWork && expanded && (
        <div className="space-y-3">
          {/* Current phase */}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-3 py-1.5 text-xs font-bold ${activity.running ? "bg-[#2c463f] text-white" : "bg-[#f2efe6] text-[#20302c]"}`}
            >
              {activity.label ?? "…"}
            </span>
            {activity.hint && (
              <span className="text-xs text-[#8a978f]">{activity.hint}</span>
            )}
            {activity.running && (
              <span className="ml-auto inline-flex items-center gap-1.5 text-xs font-medium text-[#2f7e72]">
                <StatusDot running /> agent is working
              </span>
            )}
          </div>

          {/* Pipeline rail — only for the trade chain */}
          {inChain && (
            <ol className="flex items-center gap-1.5">
              {FLOW.map((f, i) => {
                const isCurrent = i === activity.step - 1;
                const isDone = i < activity.step - 1;
                return (
                  <li key={f.step} className="flex items-center gap-1.5">
                    <span
                      className={`step-dot grid h-5 w-5 place-items-center rounded-full text-[10px] font-bold ${isDone ? "bg-[#3f9a8f] text-white" : isCurrent ? "bg-[#2c463f] text-white" : "bg-[#f2efe6] text-[#8a978f]"}`}
                    >
                      {f.label[0]}
                    </span>
                    <span
                      className={`hidden text-[10px] font-medium sm:inline ${isDone ? "text-[#8a978f]" : isCurrent ? "text-[#20302c]" : "text-[#b9c2bb]"}`}
                    >
                      {f.label}
                    </span>
                    {i < FLOW.length - 1 && (
                      <span className="h-px w-4 bg-[#e4e0d4]">
                        <span
                          className={`connector block h-px ${i < activity.step - 1 ? "bg-[#3f9a8f]" : "bg-transparent"}`}
                        />
                      </span>
                    )}
                  </li>
                );
              })}
            </ol>
          )}

          {/* Tool call chips */}
          {activity.tools.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {activity.tools.slice(0, 6).map((t) => (
                <ToolChip key={t.index} tool={t} />
              ))}
              {activity.tools.length > 6 && (
                <span className="rounded-full bg-[#f6f2e9] px-3 py-1.5 text-[11px] text-[#8a978f]">
                  +{activity.tools.length - 6} more
                </span>
              )}
            </div>
          )}

          {/* Live transcription */}
          {(activity.text || activity.reason) && (
            <div className="rounded-2xl bg-[#f6f2e9] px-4 py-3">
              {activity.reason && (
                <p className="mb-1 flex gap-2 text-xs leading-relaxed text-[#8a978f]">
                  <span className="mt-0.5 shrink-0 font-semibold">thinking</span>
                  <span className="tool-feed min-w-0 font-mono">
                    {activity.reason}
                    <span className="animate-caret text-[#3f9a8f]">▍</span>
                  </span>
                </p>
              )}
              {activity.text && (
                <p className="flex gap-2 text-xs leading-relaxed text-[#4a5751]">
                  <span className="mt-0.5 shrink-0 font-semibold text-[#2c463f]">
                    agent
                  </span>
                  <span className="tool-feed min-w-0 font-mono">
                    {activity.text}
                    {activity.running && (
                      <span className="animate-caret text-[#3f9a8f]">▍</span>
                    )}
                  </span>
                </p>
              )}
            </div>
          )}

          {activity.error && (
            <div className="flex items-start gap-2 rounded-2xl bg-[#f3e2df] px-4 py-3 text-xs text-[#b34e42]">
              <Ic name="alert" className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span className="min-w-0 break-words">{activity.error}</span>
            </div>
          )}

          {/* Event log */}
          {activity.log.length > 0 && (
            <div>
              <ul className="space-y-1">
                {visibleLog.map((entry, i) => (
                  <li
                    key={activity.log.length - visibleLog.length + i}
                    className="animate-slide-in-right flex items-center gap-2 text-[11px] leading-relaxed"
                  >
                    <Ic
                      name={LOG_ICON[entry.kind] ?? "activity"}
                      className={`h-3 w-3 shrink-0 ${entry.kind === "error" ? "text-[#c65b4e]" : "text-[#8a978f]"}`}
                    />
                    <span
                      className={entry.kind === "error" ? "text-[#c65b4e]" : "text-[#4a5751]"}
                    >
                      {entry.message}
                    </span>
                  </li>
                ))}
              </ul>
              {activity.log.length > 5 && (
                <button
                  onClick={() => setShowAll((s) => !s)}
                  className="mt-1 text-[11px] font-semibold text-[#8a978f] transition hover:text-[#2c463f]"
                >
                  {showAll ? "show less" : `show all ${activity.log.length}`}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}