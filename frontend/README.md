# Frontend — Trading Dashboard

The orchestration dashboard for the **fifty-shades-of-agent** project. A Next.js 16
(React 19, Tailwind 4) app that drives the three MCP servers
(`news-scraper`, `technical-analyst`, `trader`) through a **TrueForge**
coordinating agent and streams its live work to the browser.

## What this folder does

This folder is the **human-facing control panel** of the trading system. Instead of
talking to the MCP servers directly, the browser talks to a TrueForge agent
(`@truefoundry/trueforge-sdk`) that can call all three servers; the dashboard shows
that agent working in real time — reasoning, tool calls, and pipeline phases — as a
live activity feed plus a chat pane.

## Folder structure

```
frontend/
├── app/
│   ├── layout.tsx           # root layout
│   ├── page.tsx             # TrueForge Assistant dashboard entry point
│   ├── globals.css
│   ├── components/
│   │   ├── Dashboard.tsx    # main trading UI (~stepper/phase view, positions)
│   │   ├── AgentActivity.tsx# live logger of agent reasoning & tool calls
│   │   └── Chat.tsx         # assistant chat interface
│   └── api/
│       ├── agent/route.ts   # SSE stream that drives the TrueForge agent
│       └── sessions/
│           ├── route.ts     # REST: list/save exploration sessions
│           └── [id]/route.ts# REST: fetch/update a single session
├── lib/
│   ├── agent.ts             # SSE streaming client + typed event/result models
│   ├── sessions.ts          # session data shapes + fetch/save helpers
│   └── db.ts                # server-side pg pool (agent_sessions table)
├── public/                  # static assets
├── package.json             # bun-managed, "scripts" use `bun --bun next ...`
└── .env.local               # DATABASE_URL for Neon (do not commit)
```

## How it works

- The dashboard triggers **action-based** pipeline phases by POSTing
  `{ action, params, sessionId }` to `app/api/agent/route.ts`.
- That route builds a TrueForge client (authenticating server-side) and returns a
  **Server-Sent Events** stream with events for session id, phase metadata, MCP
  connections, incremental text/reasoning, and individual tool calls
  (`tool.start` / `tool.args` / `tool.done`).
- `lib/agent.ts` parses that stream into typed `AgentEvent`s the UI renders.
- Agent exploration sessions are persisted to Neon via `app/api/sessions/` and
  `lib/sessions.ts` (backed by `lib/db.ts`).

## Getting Started

Prerequisites: [Bun](https://bun.sh) (the package manager is `bun@1.3.14`).

```bash
bun install        # install dependencies
# ensure .env.local has DATABASE_URL pointing at your Neon Postgres
bun run dev        # starts the dev server on http://localhost:3000
```

Other scripts (see `package.json`):

```bash
bun run build      # production build
bun run start      # production server
bun run lint       # eslint
```

> **Note:** this is a customized Next.js 16 app — read `node_modules/next/dist/docs/`
> before changing Next.js-specific code, since APIs may differ from older versions.

## Connection to the rest of the repo

The dashboard does not talk to Postgres or the MCP servers directly for trading; it
relies on the TrueForge agent, which itself is wired to the three MCP servers under
`news-scraper/`, `technical-analyst/`, and `trader/`. See the root `README.md` for how
those layers fit together.
