"""Rapporto della strada 1 sui dati veri (spec §10, ultimo punto).

Carica la tabella mensile controllandone lo SHA-256, calcola tutte le misure con
path1_backtest.all_measures e scrive un JSON in data/reports/path1/ con nome unico
e scrittura esclusiva (mai sovrascritto). Nel file: ora UTC, commit Git del codice,
commit della spec, SHA-256 della tabella.

Si esegue UNA sola volta, sui dati veri, solo dopo la revisione esterna e il
confronto con la seconda implementazione.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import uuid

from src.exclusive_write import write_text_exclusive
from src.path1_backtest import all_measures, load_monthly_table


TABLE = Path("data/processed/path1_monthly.csv")
TABLE_SHA256 = "55fbfc19df2164bb7d85a4063436a240c3842053e5c5b8f7007f9117228fcf90"
SPEC = Path("docs/STRADA1_SPEC_TEST.md")
OUTPUT_DIR = Path("data/reports/path1")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True,
                          text=True).stdout.strip()


def git_info(spec: Path = SPEC) -> dict:
    """Commit del codice, commit dell'ultima modifica della spec e se ci sono
    modifiche non salvate nei file tracciati."""
    return {
        "code_commit": _git("rev-parse", "HEAD"),
        "spec_commit": _git("log", "-1", "--format=%H", "--", str(spec)),
        "uncommitted_changes": bool(_git("status", "--porcelain", "--untracked-files=no")),
    }


def write_report(table_path: Path = TABLE, expected_sha256: str = TABLE_SHA256,
                 output_dir: Path = OUTPUT_DIR, spec: Path = SPEC, **measures_kwargs) -> Path:
    table = load_monthly_table(table_path, expected_sha256)
    measures = all_measures(table, **measures_kwargs)

    created_at = datetime.now(timezone.utc)
    report = {
        "created_at_utc": created_at.isoformat(),
        **git_info(spec),
        "table": str(table_path),
        "table_sha256": expected_sha256,
        "spec": str(spec),
        "measures": measures,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (
        f"path1_report_{created_at.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}.json"
    )
    write_text_exclusive(path, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return path


def main() -> None:
    path = write_report()
    print(f"Rapporto: {path}")


if __name__ == "__main__":
    main()
