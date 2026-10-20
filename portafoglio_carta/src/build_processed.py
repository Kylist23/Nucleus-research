"""Costruisce data/processed/eur_usd_daily.parquet a partire dalle acquisizioni
ECB e H.10 oggi valide (quelle in data/raw/). Un valore mancante resta vuoto
(NaN), non diventa zero. Rieseguendo con gli stessi file di input il risultato
deve essere identico: vedi tests/test_processed_data.py.
"""

from pathlib import Path

import pandas as pd

from src.h10_parsing import load_eur_series


DEFAULT_ECB_FILE = Path("data/raw/ecb/eur_usd_ecb_raw.csv")
DEFAULT_H10_FILE = Path("data/raw/h10/h10_20260920T150631Z_3a34cb9c.csv")
DEFAULT_OUTPUT_FILE = Path("data/processed/eur_usd_daily.parquet")


def _load_ecb(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    return pd.DataFrame(
        {
            "date": pd.to_datetime(df["TIME_PERIOD"]).dt.date,
            "ecb_rate": pd.to_numeric(df["OBS_VALUE"], errors="coerce"),
        }
    )


def _load_h10(path: Path) -> pd.DataFrame:
    observations = load_eur_series(path)

    dates = []
    values = []

    for date_text, value_text in observations:
        dates.append(pd.to_datetime(date_text).date())
        values.append(
            float("nan") if value_text == "ND" else float(value_text)
        )

    return pd.DataFrame({"date": dates, "h10_rate": values})


def build(
    ecb_file: Path = DEFAULT_ECB_FILE,
    h10_file: Path = DEFAULT_H10_FILE,
) -> pd.DataFrame:
    ecb = _load_ecb(ecb_file)
    h10 = _load_h10(h10_file)

    merged = ecb.merge(h10, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    return merged[["date", "ecb_rate", "h10_rate"]]


def main() -> None:
    df = build()

    DEFAULT_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DEFAULT_OUTPUT_FILE, index=False)

    print("Processed dataset built.")
    print(f"File: {DEFAULT_OUTPUT_FILE}")
    print(f"Rows: {len(df)}")
    print(f"First date: {df['date'].min()}")
    print(f"Last date:  {df['date'].max()}")
    print(f"Missing ecb_rate: {df['ecb_rate'].isna().sum()}")
    print(f"Missing h10_rate: {df['h10_rate'].isna().sum()}")


if __name__ == "__main__":
    main()
