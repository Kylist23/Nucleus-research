"""Scarica lo storico ECB (EUR/USD) e lo salva con nome unico.

Stesso modello di src/acquire_h10.py: ogni esecuzione crea un file nuovo
(mai sovrascrive uno esistente) e registra il tentativo in
data/logs/acquisition_attempts.jsonl, che vada a buon fine o no.

Il file scaricato prima di queste regole (data/raw/ecb/eur_usd_ecb_raw.csv)
non viene toccato: resta la base dati usata finché non se ne farà una nuova
acquisizione con questo script (vedi data/raw/ecb/PRE_RULES_NOTE.md).
"""

from pathlib import Path
from datetime import datetime, timezone
import csv
import io
import json
import uuid

import requests

from src.hashing import sha256_file, sha256_bytes
from src.exclusive_write import write_exclusive, write_text_exclusive
from src.attempt_log import log_attempt


SOURCE_ID = "ecb"
SERIES_ID = "EXR.D.USD.EUR.SP00.A"

URL = (
    "https://data-api.ecb.europa.eu/service/data/"
    "EXR/D.USD.EUR.SP00.A"
    "?startPeriod=1999-01-04"
    "&format=csvdata"
)

DESCRIPTION = "Daily US dollar per euro exchange rate"
START_PERIOD = "1999-01-04"

DEFAULT_OUTPUT_DIR = Path("data/raw/ecb")
DEFAULT_ATTEMPTS_LOG = Path("data/logs/acquisition_attempts.jsonl")
DOWNLOADER_VERSION = "nucleus-ecb-0.3"


def _count_rows(data: bytes) -> int:
    """Numero di righe di dati (esclusa l'intestazione), contate sui byte."""
    rows = list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))

    return max(len(rows) - 1, 0)


def run(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    attempts_log: Path = DEFAULT_ATTEMPTS_LOG,
    url: str = URL,
    fetch=None,
    series_id: str = SERIES_ID,
    description: str = DESCRIPTION,
    start_period: str | None = START_PERIOD,
) -> dict:
    """Esegue un tentativo di acquisizione. `fetch` è la funzione usata per fare
    la richiesta HTTP (di default requests.get): iniettabile per i test.
    `series_id`, `description` e `start_period` finiscono nei metadati: i
    valori di default sono quelli della serie EUR/USD giornaliera."""
    if fetch is None:
        fetch = requests.get

    output_dir.mkdir(parents=True, exist_ok=True)

    retrieved_at = datetime.now(timezone.utc)
    acquisition_id = (
        f"ecb_{retrieved_at.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    )
    data_file = output_dir / f"{acquisition_id}.csv"
    metadata_file = output_dir / f"{acquisition_id}.json"

    try:
        response = fetch(url, timeout=60, headers={"User-Agent": "Nucleus/0.1"})
        response.raise_for_status()
    except Exception as exc:
        log_attempt(
            attempts_log,
            source_id=SOURCE_ID,
            url=url,
            script_version=DOWNLOADER_VERSION,
            outcome="FAILED",
            http_status=getattr(getattr(exc, "response", None), "status_code", None),
            error=str(exc),
        )
        raise

    # i byte si leggono una volta sola: impronta, dimensione e righe vengono da qui
    data = response.content
    size = len(data)
    try:
        digest = sha256_bytes(data)
        row_count = _count_rows(data)

        write_exclusive(data_file, data)
        written = sha256_file(data_file)
        if written != digest:
            raise ValueError(
                f"SHA-256 del file scritto diverso dai byte ricevuti: {written} != {digest}"
            )

        metadata = {
            "acquisition_id": acquisition_id,
            "source_id": SOURCE_ID,
            "series_id": series_id,
            "description": description,
            "start_period_requested": start_period,
            "url": url,
            "retrieved_at": retrieved_at.isoformat(),
            "http_status": response.status_code,
            "raw_file": str(data_file),
            "sha256": digest,
            "file_size_bytes": size,
            "downloader_version": DOWNLOADER_VERSION,
            "row_count": row_count,
        }

        write_text_exclusive(metadata_file, json.dumps(metadata, indent=2))
    except Exception as exc:
        # mai cancellare niente in data/raw: si registra il fallimento e ci si ferma
        log_attempt(
            attempts_log,
            source_id=SOURCE_ID,
            url=url,
            script_version=DOWNLOADER_VERSION,
            outcome="FAILED",
            http_status=response.status_code,
            size_bytes=size,
            error=f"{type(exc).__name__}: {exc}",
        )
        raise

    log_attempt(
        attempts_log,
        source_id=SOURCE_ID,
        url=url,
        script_version=DOWNLOADER_VERSION,
        outcome="SUCCESS",
        http_status=response.status_code,
        size_bytes=size,
    )

    return metadata


def main() -> None:
    metadata = run()

    print("ECB acquisition completed.")
    print(f"Acquisition: {metadata['acquisition_id']}")
    print(f"Data:        {metadata['raw_file']}")
    print(f"SHA-256:     {metadata['sha256']}")
    print(f"Rows:        {metadata['row_count']}")


if __name__ == "__main__":
    main()
