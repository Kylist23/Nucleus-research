from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import json

from src.hashing import sha256_file
from src.h10_parsing import load_eur_series


INPUT_DIR = Path("data/raw/h10")
REPORT_DIR = Path("data/reports/h10")

ACQUISITION_ID = "h10_20260920T150631Z_3a34cb9c"
DATA_FILE = INPUT_DIR / f"{ACQUISITION_ID}.csv"
META_FILE = INPUT_DIR / f"{ACQUISITION_ID}.json"
REPORT_FILE = REPORT_DIR / f"{ACQUISITION_ID}_quality_report.json"

SERIES_ID = "H10/H10/RXI$US_N.B.EU"
UNIT = "USD_per_EUR"


def main() -> None:
    metadata = json.loads(
        META_FILE.read_text(encoding="utf-8")
    )

    observations = load_eur_series(DATA_FILE)

    dates = []
    valid_values = []
    nd_count = 0
    invalid_dates = 0

    for date_text, value_text in observations:
        try:
            datetime.strptime(date_text, "%Y-%m-%d")
            dates.append(date_text)
        except ValueError:
            invalid_dates += 1
            continue

        if value_text == "ND":
            nd_count += 1
            continue

        try:
            value = Decimal(value_text)
        except Exception:
            continue

        valid_values.append(value)

    duplicate_dates = len(dates) - len(set(dates))
    sorted_dates = dates == sorted(dates)
    non_positive_values = sum(
        value <= 0 for value in valid_values
    )

    actual_hash = sha256_file(DATA_FILE)
    hash_matches = actual_hash == metadata["sha256"]

    report = {
        "acquisition_id": ACQUISITION_ID,
        "source_id": "federal_reserve_h10",
        "series_id": SERIES_ID,
        "unit": UNIT,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),

        "raw_file": str(DATA_FILE),
        "metadata_file": str(META_FILE),

        "integrity": {
            "sha256_file": actual_hash,
            "sha256_metadata": metadata["sha256"],
            "hash_matches": hash_matches,
        },

        "observations": {
            "total_rows": len(observations),
            "valid_observations": len(valid_values),
            "nd_observations": nd_count,
            "invalid_dates": invalid_dates,
            "duplicate_dates": duplicate_dates,
            "chronologically_sorted": sorted_dates,
            "non_positive_values": non_positive_values,
        },

        "coverage": {
            "first_observation_date": dates[0] if dates else None,
            "last_observation_date": dates[-1] if dates else None,
        },

        "values": {
            "minimum": str(min(valid_values)) if valid_values else None,
            "maximum": str(max(valid_values)) if valid_values else None,
        },

        "quality_status": (
            "PASS"
            if (
                hash_matches
                and invalid_dates == 0
                and duplicate_dates == 0
                and sorted_dates
                and non_positive_values == 0
                and nd_count == metadata["nd_observations"]
                and len(valid_values) == metadata["valid_observations"]
            )
            else "FAIL"
        ),
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("H.10 quality report generated.")
    print(f"Report: {REPORT_FILE}")
    print(f"Status: {report['quality_status']}")
    print(f"Rows:   {report['observations']['total_rows']}")
    print(f"Valid:  {report['observations']['valid_observations']}")
    print(f"ND:     {report['observations']['nd_observations']}")


if __name__ == "__main__":
    main()
