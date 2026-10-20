from pathlib import Path
import json

import pandas as pd

from src.hashing import sha256_file


DATA_FILE = Path("data/raw/ecb/eur_usd_ecb_raw.csv")
META_FILE = Path("data/raw/ecb/eur_usd_ecb_acquisition.json")


def load_ecb():
    assert DATA_FILE.exists()
    return pd.read_csv(DATA_FILE)


def test_ecb_file_contains_data():
    df = load_ecb()

    assert len(df) > 0


def test_ecb_dates_are_valid():
    df = load_ecb()

    dates = pd.to_datetime(df["TIME_PERIOD"], errors="coerce")

    assert dates.isna().sum() == 0


def test_ecb_dates_are_unique():
    df = load_ecb()

    dates = pd.to_datetime(df["TIME_PERIOD"])

    assert dates.duplicated().sum() == 0


def test_ecb_is_chronologically_sorted():
    df = load_ecb()

    dates = pd.to_datetime(df["TIME_PERIOD"])

    assert dates.is_monotonic_increasing


def test_ecb_values_are_positive():
    df = load_ecb()

    values = pd.to_numeric(df["OBS_VALUE"], errors="coerce").dropna()

    assert (values <= 0).sum() == 0


def test_ecb_file_hash_matches_metadata():
    expected_hash = json.loads(
        META_FILE.read_text(encoding="utf-8")
    )["sha256"]

    assert sha256_file(DATA_FILE) == expected_hash
