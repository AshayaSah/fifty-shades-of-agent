import json
from datetime import datetime, timezone

AUDIT_FILE = "audit_log.jsonl"


def log_event(event_type: str, data: dict) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        **data,
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
