// GET /api/sessions — list persisted exploration sessions (newest first).
import { NextResponse } from "next/server";

import { ensureSchema, pool } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  if (!pool) {
    return NextResponse.json({ error: "DATABASE_URL is not set" }, { status: 500 });
  }
  await ensureSchema();
  const { rows } = await pool.query(
    `SELECT id, title, symbol, created_at AS "createdAt", updated_at AS "updatedAt"
     FROM agent_sessions
     WHERE kind = 'explore'
     ORDER BY updated_at DESC
     LIMIT 100`,
  );
  return NextResponse.json({ sessions: rows });
}