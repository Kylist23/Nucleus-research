"""Scarica lo storico H.10 (Federal Reserve) e lo salva con nome unico.

Ogni esecuzione crea un file nuovo (mai sovrascrive uno esistente) e registra
il tentativo in data/logs/acquisition_attempts.jsonl, che vada a buon fine o no.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
import uuid

import requests

from src.hashing import sha256_file
from src.exclusive_write import write_exclusive, write_text_exclusive
from src.attempt_log import log_attempt
from src.h10_parsing import load_eur_series


SOURCE_ID = "federal_reserve_h10"
SERIES_ID = "H10/H10/RXI$US_N.B.EU"
UNIT = "USD_per_EUR"

URL = (
    "https://www.federalreserve.gov/datadownload/Output.aspx"
    "?rel=H10"
    "&series=60f32914ab61dfab590e0e470153e3ae"
    "&from=1999-01-04"
    "&to=2026-09-18"
    "&filetype=csv"
    "&label=include"
    "&layout=seriescolumn"
    "&type=package"
)

DEFAULT_OUTPUT_DIR = Path("data/raw/h10")
DEFAULT_ATTEMPTS_LOG = Path("data/logs/acquisition_attempts.jsonl")
DOWNLOADER_VERSION = "nucleus-h10-0.2"


def _summarize_series(path: Path) -> dict:
    observations = load_eur_series(path)

    dates = []
    valid_values = []
    nd_count = 0

    for date, value in observations:
        if value == "ND":
            nd_count += 1
            continue

        dates.append(date)
        valid_values.append(value)

    return {
        "observation_rows": len(observations),
        "valid_observations": len(valid_values),
        "nd_observations": nd_count,
        "first_observation_date": dates[0] if dates else None,
        "last_observation_date": dates[-1] if dates else None,
    }


def run(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    attempts_log: Path = DEFAULT_ATTEMPTS_LOG,
    url: str = URL,
    fetch=None,
) -> dict:
    """Esegue un tentativo di acquisizione. `fetch` è la funzione usata per fare
    la richiesta HTTP (di default requests.get): iniettabile per i test, così
    si può simulare un fallimento senza toccare la rete."""
    if fetch is None:
        fetch = requests.get

    output_dir.mkdir(parents=True, exist_ok=True)

    retrieved_at = datetime.now(timezone.utc)
    acquisition_id = (
        f"h10_{retrieved_at.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
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

    try:
        write_exclusive(data_file, response.content)
    except FileExistsError as exc:
        log_attempt(
            attempts_log,
            source_id=SOURCE_ID,
            url=url,
            script_version=DOWNLOADER_VERSION,
            outcome="FAILED",
            http_status=response.status_code,
            error=f"Il file esiste già, non sovrascritto: {data_file}",
        )
        raise

    series_info = _summarize_series(data_file)

    metadata = {
        "acquisition_id": acquisition_id,
        "source_id": SOURCE_ID,
        "series_id": SERIES_ID,
        "unit": UNIT,
        "retrieved_at": retrieved_at.isoformat(),
        "http_status": response.status_code,
        "url": url,
        "raw_file": str(data_file),
        "sha256": sha256_file(data_file),
        "file_size_bytes": data_file.stat().st_size,
        "downloader_version": DOWNLOADER_VERSION,
        "series_description": "Euro-Area Euro",
        **series_info,
    }

    write_text_exclusive(metadata_file, json.dumps(metadata, indent=2))

    log_attempt(
        attempts_log,
        source_id=SOURCE_ID,
        url=url,
        script_version=DOWNLOADER_VERSION,
        outcome="SUCCESS",
        http_status=response.status_code,
        size_bytes=metadata["file_size_bytes"],
    )

    return metadata


def main() -> None:
    metadata = run()

    print("H.10 acquisition completed.")
    print(f"Acquisition: {metadata['acquisition_id']}")
    print(f"Data:        {metadata['raw_file']}")
    print(f"SHA-256:     {metadata['sha256']}")
    print(f"Observations:{metadata['valid_observations']}")
    print(f"ND:          {metadata['nd_observations']}")
    print(f"Last date:   {metadata['last_observation_date']}")


if __name__ == "__main__":
    main()
