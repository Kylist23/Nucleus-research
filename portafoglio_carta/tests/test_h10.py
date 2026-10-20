from pathlib import Path
import json

import pandas as pd

from src.hashing import sha256_file
from src.h10_parsing import load_eur_series


ACQUISITION_ID = "h10_20260920T150631Z_3a34cb9c"

DATA_FILE = Path(
    f"data/raw/h10/{ACQUISITION_ID}.csv"
)

META_FILE = Path(
    f"data/raw/h10/{ACQUISITION_ID}.json"
)

REPORT_FILE = Path(
    f"data/reports/h10/{ACQUISITION_ID}_quality_report.json"
)


def load_metadata():
    return json.loads(
        META_FILE.read_text(encoding="utf-8")
    )


def load_report():
    return json.loads(
        REPORT_FILE.read_text(encoding="utf-8")
    )


def test_h10_data_exists():
    assert DATA_FILE.exists()


def test_h10_metadata_exists():
    assert META_FILE.exists()


def test_h10_quality_report_exists():
    assert REPORT_FILE.exists()


def test_h10_hash_matches_metadata():
    metadata = load_metadata()

    assert sha256_file(DATA_FILE) == metadata["sha256"]


def test_h10_quality_status_is_pass():
    report = load_report()

    assert report["quality_status"] == "PASS"


def test_h10_dates_are_valid_unique_and_sorted():
    observations = load_eur_series(DATA_FILE)

    dates = pd.to_datetime(
        [date for date, _ in observations],
        errors="coerce",
    )

    assert dates.notna().all()
    assert dates.is_unique
    assert dates.is_monotonic_increasing


def test_h10_eur_values_are_positive():
    observations = load_eur_series(DATA_FILE)

    values = pd.to_numeric(
        pd.Series(
            value for _, value in observations
            if value != "ND"
        ),
        errors="coerce",
    ).dropna()

    assert (values > 0).all()


def test_h10_expected_observation_counts():
    metadata = load_metadata()
    report = load_report()

    assert report["observations"]["total_rows"] == 7225
    assert (
        report["observations"]["valid_observations"]
        == metadata["valid_observations"]
    )
    assert (
        report["observations"]["nd_observations"]
        == metadata["nd_observations"]
    )


def test_h10_coverage():
    report = load_report()

    assert (
        report["coverage"]["first_observation_date"]
        == "1999-01-04"
    )

    assert (
        report["coverage"]["last_observation_date"]
        == "2026-09-11"
    )
