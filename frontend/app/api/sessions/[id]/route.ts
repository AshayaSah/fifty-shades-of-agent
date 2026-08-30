// GET/PUT/DELETE /api/sessions/[id] — fetch a session snapshot, upsert one,
// or delete it.
import { NextRequest, NextResponse } from "next/server";

import { ensureSchema, pool } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };

const noDb = () =>
  NextResponse.json({ error: "DATABASE_URL is not set" }, { status: 500 });

export async function GET(_req: NextRequest, { params }: Params) {
  const { id } = await params;
  if (!pool) return noDb();
  await ensureSchema();
  const { rows } = await pool.query(
    `SELECT id, kind, title, symbol, snapshot, created_at AS "createdAt",
            updated_at AS "updatedAt"
     FROM agent_sessions WHERE id = $1`,
    [id],
  );
  if (!rows.length) {
    return NextResponse.json({ error: "Session not found" }, { status: 404 });
  }
  const row = rows[0];
  return NextResponse.json({
    session: {
      id: row.id,
      title: row.title,
      symbol: row.symbol,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    },
    snapshot: row.snapshot,
  });
}

export async function PUT(req: NextRequest, { params }: Params) {
  const { id } = await params;
  const body = await req.json().catch(() => null);
  if (!body || body.snapshot == null) {
    return NextResponse.json({ error: "snapshot is required" }, { status: 400 });
  }
  if (!pool) return noDb();
  await ensureSchema();
  const kind = typeof body.kind === "string" ? body.kind : "explore";
  const title = typeof body.title === "string" ? body.title : null;
  const symbol = typeof body.symbol === "string" ? body.symbol : null;
  await pool.query(
    `INSERT INTO agent_sessions (id, kind, title, symbol, snapshot, updated_at)
     VALUES ($1, $2, $3, $4, $5, now())
     ON CONFLICT (id) DO UPDATE SET
       kind = EXCLUDED.kind,
       title = EXCLUDED.title,
       symbol = EXCLUDED.symbol,
       snapshot = EXCLUDED.snapshot,
       updated_at = now()`,
    [id, kind, title, symbol, JSON.stringify(body.snapshot)],
  );
  return NextResponse.json({ ok: true });
}

export async function DELETE(_req: NextRequest, { params }: Params) {
  const { id } = await params;
  if (!pool) return noDb();
  await ensureSchema();
  await pool.query(`DELETE FROM agent_sessions WHERE id = $1`, [id]);
  return NextResponse.json({ ok: true });
}