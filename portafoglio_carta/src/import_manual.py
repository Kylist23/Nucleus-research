"""Importa in data/raw/ un file scaricato a mano (per esempio da Stooq con il browser).

Stesse regole degli script di download (vedi CLAUDE.md, Regole dei dati):
- l'originale viene copiato senza modifiche, con nome unico e scrittura esclusiva;
- prima si controlla lo SHA-256 dell'originale: se non è quello atteso ci si ferma;
- ogni importazione, riuscita o fallita, va nel registro dei tentativi.
"""

from pathlib import Path
from datetime import datetime, timezone
import csv
import io
import json
import uuid

from src.hashing import sha256_file, sha256_bytes
from src.exclusive_write import write_exclusive, write_text_exclusive
from src.attempt_log import log_attempt


DEFAULT_ATTEMPTS_LOG = Path("data/logs/acquisition_attempts.jsonl")
IMPORTER_VERSION = "nucleus-import-manual-0.2"
METHOD = "manual_browser_download"


def _count_rows(data: bytes) -> int:
    """Numero di righe di dati (esclusa l'intestazione), contate sui byte."""
    rows = list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))

    return max(len(rows) - 1, 0)


def import_file(
    original: Path,
    expected_sha256: str,
    source_id: str,
    output_dir: Path,
    attempts_log: Path = DEFAULT_ATTEMPTS_LOG,
    description: str = "",
) -> dict:
    """Copia `original` in `output_dir` con nome unico e ne scrive i metadati.

    I byte dell'originale si leggono una volta sola: impronta, dimensione, righe e
    copia vengono tutti da quei byte. Solleva ValueError se lo SHA-256 non è
    `expected_sha256` (in quel caso non copia niente). Ogni errore viene registrato
    come tentativo fallito; nessun file in data/raw viene mai cancellato.
    """
    original = Path(original)
    url = original.resolve().as_uri()
    size = None

    def _fail(exc: Exception) -> None:
        log_attempt(
            attempts_log,
            source_id=source_id,
            url=url,
            script_version=IMPORTER_VERSION,
            outcome="FAILED",
            size_bytes=size,
            error=f"{type(exc).__name__}: {exc}",
        )

    try:
        data = original.read_bytes()
        size = len(data)
        digest = sha256_bytes(data)
        if digest != expected_sha256:
            raise ValueError(
                f"SHA-256 diverso da quello atteso per {original.name}: "
                f"{digest} invece di {expected_sha256}"
            )
    except Exception as exc:
        _fail(exc)
        raise

    try:
        row_count = _count_rows(data)
        original_mtime = datetime.fromtimestamp(original.stat().st_mtime, tz=timezone.utc)

        output_dir.mkdir(parents=True, exist_ok=True)
        imported_at = datetime.now(timezone.utc)
        import_id = (
            f"{source_id}_{original.stem}_"
            f"{imported_at.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
        )
        data_file = output_dir / f"{import_id}{original.suffix}"
        metadata_file = output_dir / f"{import_id}.json"

        write_exclusive(data_file, data)
        written = sha256_file(data_file)
        if written != digest:
            raise ValueError(f"SHA-256 della copia diverso: {written} != {digest}")

        metadata = {
            "acquisition_id": import_id,
            "source_id": source_id,
            "description": description,
            "method": METHOD,
            "original_path": str(original.resolve()),
            "original_name": original.name,
            "original_modified_at": original_mtime.isoformat(),
            "imported_at": imported_at.isoformat(),
            "raw_file": str(data_file),
            "sha256": digest,
            "sha256_matches_original": written == digest,
            "file_size_bytes": size,
            "importer_version": IMPORTER_VERSION,
            "row_count": row_count,
        }

        write_text_exclusive(metadata_file, json.dumps(metadata, indent=2))
    except Exception as exc:
        _fail(exc)
        raise

    log_attempt(
        attempts_log,
        source_id=source_id,
        url=url,
        script_version=IMPORTER_VERSION,
        outcome="SUCCESS",
        size_bytes=size,
    )

    return metadata
