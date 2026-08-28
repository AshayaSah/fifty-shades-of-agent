import json
import uuid
from datetime import datetime, timezone

import db

_store: dict[str, dict] = {}


def _row_to_dict(row) -> dict:
    result = row[9]
    if isinstance(result, str):
        result = json.loads(result) if result else None
    return {
        "id": row[0],
        "symbol": row[1],
        "direction": row[2],
        "entry": row[3],
        "sl": row[4],
        "tp": row[5],
        "rationale": row[6],
        "status": row[7],
        "created_at": row[8].isoformat() if hasattr(row[8], "isoformat") else row[8],
        "result": result,
    }


def create_proposal(
    symbol: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    rationale: str,
) -> dict:
    proposal_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    proposal = {
        "id": proposal_id,
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "rationale": rationale,
        "status": "pending",
        "created_at": created_at.isoformat(),
    }
    conn = db._get_conn()
    conn.execute(
        """
        INSERT INTO proposals
            (id, symbol, direction, entry, sl, tp, rationale, status, created_at, result)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
        """,
        (
            proposal_id,
            symbol,
            direction,
            entry,
            sl,
            tp,
            rationale,
            "pending",
            created_at,
        ),
    )
    _store[proposal_id] = proposal
    return proposal


def get_proposal(proposal_id: str) -> dict | None:
    if proposal_id in _store:
        return _store[proposal_id]
    conn = db._get_conn()
    row = conn.execute(
        "SELECT id, symbol, direction, entry, sl, tp, rationale, status, created_at, result "
        "FROM proposals WHERE id = %s",
        (proposal_id,),
    ).fetchone()
    if row is None:
        return None
    proposal = _row_to_dict(row)
    _store[proposal_id] = proposal
    return proposal


def update_proposal_status(
    proposal_id: str, status: str, result: dict | None = None
) -> dict | None:
    proposal = get_proposal(proposal_id)
    if proposal is None:
        return None
    proposal["status"] = status
    if result is not None:
        proposal["result"] = result
    conn = db._get_conn()
    conn.execute(
        "UPDATE proposals SET status = %s, result = %s WHERE id = %s",
        (status, json.dumps(result) if result is not None else None, proposal_id),
    )
    return proposal
