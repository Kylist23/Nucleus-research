"""Registro dei tentativi di download: una riga JSON per ogni esecuzione,
riuscita o fallita. File di log in formato JSONL (un oggetto JSON per riga)."""

from pathlib import Path
from datetime import datetime, timezone
import json


def log_attempt(
    log_path: Path,
    *,
    source_id: str,
    url: str,
    script_version: str,
    outcome: str,
    http_status: int | None = None,
    size_bytes: int | None = None,
    error: str | None = None,
) -> None:
    """Aggiunge una riga al registro dei tentativi.

    outcome: "SUCCESS" oppure "FAILED".
    """
    if outcome not in ("SUCCESS", "FAILED"):
        raise ValueError(f"outcome deve essere SUCCESS o FAILED, non {outcome!r}")

    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_id": source_id,
        "url": url,
        "script_version": script_version,
        "outcome": outcome,
        "http_status": http_status,
        "size_bytes": size_bytes,
        "error": error,
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
