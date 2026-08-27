import uuid
from datetime import datetime, timezone

_store: dict[str, dict] = {}


def create_proposal(
    symbol: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    rationale: str,
) -> dict:
    proposal_id = str(uuid.uuid4())
    proposal = {
        "id": proposal_id,
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "rationale": rationale,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _store[proposal_id] = proposal
    return proposal


def get_proposal(proposal_id: str) -> dict | None:
    return _store.get(proposal_id)


def update_proposal_status(
    proposal_id: str, status: str, result: dict | None = None
) -> dict | None:
    proposal = _store.get(proposal_id)
    if proposal is None:
        return None
    proposal["status"] = status
    if result is not None:
        proposal["result"] = result
    return proposal
