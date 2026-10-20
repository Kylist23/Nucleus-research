from pathlib import Path
from datetime import datetime, timezone
import json

import pandas as pd

from src.hashing import sha256_file


DATA_FILE = Path("data/raw/ecb/eur_usd_ecb_raw.csv")
META_FILE = Path("data/raw/ecb/eur_usd_ecb_acquisition.json")
REPORT_FILE = Path("data/reports/ecb/eur_usd_ecb_quality_report.json")


def main() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset non trovato: {DATA_FILE}")

    df = pd.read_csv(DATA_FILE)

    dates = pd.to_datetime(df["TIME_PERIOD"], errors="coerce")
    values = pd.to_numeric(df["OBS_VALUE"], errors="coerce")

    valid_values = values.dropna()

    metadata = json.loads(META_FILE.read_text(encoding="utf-8"))
 
    current_sha256 = sha256_file(DATA_FILE)
    current_size = DATA_FILE.stat().st_size
 
    metadata_sha256_matches = current_sha256 == metadata["sha256"]
    metadata_size_matches = current_size == metadata["size_bytes"]   

    date_counts = dates.value_counts()

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(DATA_FILE),
        "rows_total": len(df),
        "columns_total": len(df.columns),
        "first_date": dates.min().date().isoformat(),
        "last_date": dates.max().date().isoformat(),
        "invalid_dates": int(dates.isna().sum()),
        "missing_values": int(values.isna().sum()),
        "duplicate_dates": int(dates.duplicated().sum()),
        "multiple_rows_same_day": int((date_counts > 1).sum()),
        "max_rows_same_day": int(date_counts.max()),
        "chronologically_sorted": bool(dates.is_monotonic_increasing),
        "valid_values": int(len(valid_values)),
        "min_value": float(valid_values.min()),
        "max_value": float(valid_values.max()),
        "mean_value": float(valid_values.mean()),
        "values_less_equal_zero": int((valid_values <= 0).sum()),
        "observation_status": {
            str(k): int(v)
            for k, v in df["OBS_STATUS"].value_counts(dropna=False).items()
        },
        "file_size_bytes": DATA_FILE.stat().st_size,
        "sha256": sha256_file(DATA_FILE),
        "metadata_sha256_matches": metadata_sha256_matches,
        "metadata_size_matches": metadata_size_matches,
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("ECB quality report generated.")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
