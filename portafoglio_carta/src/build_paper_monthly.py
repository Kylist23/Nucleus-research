"""Costruisce la tabella mensile del portafoglio di carta C (docs/STRADA1_PORTAFOGLIO_CARTA.md).

- Usa i file grezzi più recenti di data/raw/: le 5 serie BCE scaricate con
  startPeriod = PAPER_START (src/paper_monthly.py) e l'oro di Stooq importato a mano.
- Controlla lo SHA-256 di ogni file contro i suoi metadati.
- Tiene SUBITO dopo la lettura, prima di qualsiasi calcolo, solo i mesi da PAPER_START
  al mese prima di quello in corso (UTC): la cassaforte 2023-01..2026-10 non entra mai
  nei calcoli, il mese in corso nemmeno.
- La tabella finisce all'ultimo mese in cui ci sono TUTTE le serie (la BCE pubblica le
  medie di un mese qualche giorno dopo la sua fine). Nessun buco, nessun valore inventato.
- Scrive data/processed/paper_c_monthly.csv e data/reports/paper/quality_paper_monthly.json.
"""

from pathlib import Path
from datetime import datetime
import json
import math

import pandas as pd

from src import build_path1_monthly as b1
from src.hashing import sha256_file
from src.path1_paper import PAPER_START, current_month


RAW = Path("data/raw")
OUTPUT_TABLE = Path("data/processed/paper_c_monthly.csv")
OUTPUT_QUALITY = Path("data/reports/paper/quality_paper_monthly.json")

# Le stesse serie della strada 1 (STRADA1_SPEC_TEST.md §1), senza Bitcoin: C e LIQ non lo usano.
ECB_SERIES = {col: b1.EXPECTED_KEYS[col] for col in
              ["spx_usd", "sx5e_eur", "y10_pct", "euribor3m_pct", "usd_per_eur"]}
GOLD_PATTERN = "stooq_xauusd_d_*.csv"

COLUMNS = ["month", "spx_usd", "sx5e_eur", "y10_pct", "euribor3m_pct", "usd_per_eur",
           "gold_usd", "spx_eur", "gold_eur"]


class PaperDataError(Exception):
    """Un controllo dei dati non è passato: ci si ferma e non si scrive niente."""


def in_window(month: str, now: datetime | None = None) -> bool:
    """True solo per i mesi da PAPER_START al mese prima di quello in corso (UTC)."""
    return PAPER_START <= month < current_month(now)


def _metadata(path: Path) -> dict:
    return json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))


def latest_ecb_file(series_id: str, raw_dir: Path = RAW) -> Path:
    """Il file BCE più recente di `series_id` scaricato a partire da PAPER_START.
    I file scaricati prima della prova (storia completa, cassaforte inclusa) non si usano."""
    found = []
    for meta_path in sorted((raw_dir / "ecb").glob("ecb_*.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("series_id") == series_id and meta.get("start_period_requested") == PAPER_START:
            found.append((meta["retrieved_at"], meta_path.with_suffix(".csv")))
    if not found:
        raise PaperDataError(f"Nessun download BCE di {series_id} a partire da {PAPER_START}")
    return max(found)[1]


def latest_gold_file(raw_dir: Path = RAW) -> Path:
    """Il file dell'oro Stooq importato per ultimo."""
    found = [(_metadata(p)["imported_at"], p) for p in (raw_dir / "stooq").glob(GOLD_PATTERN)]
    if not found:
        raise PaperDataError("Nessun file dell'oro Stooq in data/raw/stooq")
    return max(found)[1]


def read_ecb(path: Path, expected_key: str, now: datetime | None = None) -> pd.Series:
    """Serie mensile BCE, solo mesi della prova già finiti."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    raw = raw[[in_window(m, now) for m in raw["TIME_PERIOD"]]]  # finestra della prova, prima di tutto
    if set(raw["KEY"]) - {expected_key}:
        raise PaperDataError(f"{path}: chiave inattesa {set(raw['KEY'])}")
    if raw["TIME_PERIOD"].duplicated().any():
        raise PaperDataError(f"{path}: mesi duplicati")
    # come §12 del test: valore normale (A) e media del periodo (A)
    for col in ("OBS_STATUS", "COLLECTION"):
        if col not in raw.columns or set(raw[col]) - {"A"}:
            bad = sorted(set(raw[col]) - {"A"}) if col in raw.columns else "colonna assente"
            raise PaperDataError(f"{path}: {col} diverso da A: {bad}")
    values = [b1._to_float(v) for v in raw["OBS_VALUE"]]
    return pd.Series(values, index=list(raw["TIME_PERIOD"]), dtype="float64").dropna()


def read_gold(path: Path, now: datetime | None = None) -> pd.Series:
    """Media mensile delle chiusure giornaliere dell'oro, solo mesi della prova già finiti."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    raw = raw[[in_window(d[:7], now) for d in raw["Date"]]]  # finestra della prova, prima di tutto
    if raw["Date"].duplicated().any():
        raise PaperDataError(f"{path}: date duplicate")
    daily = pd.DataFrame({"date": list(raw["Date"]),
                          "value": [b1._to_float(v) for v in raw["Close"]]})
    if daily.empty:
        return pd.Series(dtype="float64")
    return b1.monthly_mean(daily)


def assemble(series: dict[str, pd.Series]) -> tuple[pd.DataFrame, dict]:
    """Una riga per mese, da PAPER_START all'ultimo mese con tutte le serie.
    Restituisce anche l'ultimo mese disponibile di ogni serie."""
    last_by_series = {col: (s.index.max() if len(s) else None) for col, s in series.items()}
    if any(v is None for v in last_by_series.values()):
        empty = sorted(c for c, v in last_by_series.items() if v is None)
        raise PaperDataError(
            f"Nessun mese della prova ancora disponibile per: {empty}. "
            f"Il primo mese ({PAPER_START}) si può calcolare solo dopo la sua fine, "
            "quando la BCE ha pubblicato le medie."
        )
    last = min(last_by_series.values())
    months = b1.months_between(PAPER_START, last)
    table = pd.DataFrame({"month": months})
    for col, s in series.items():
        table[col] = [float(s[m]) if m in s.index else math.nan for m in months]
    missing = {col: [m for m, v in zip(months, table[col]) if pd.isna(v)]
               for col in series}
    missing = {c: v for c, v in missing.items() if v}
    if missing:
        raise PaperDataError(f"Mesi mancanti: {missing}")
    table["spx_eur"] = table["spx_usd"] / table["usd_per_eur"]
    table["gold_eur"] = table["gold_usd"] / table["usd_per_eur"]
    return table[COLUMNS], last_by_series


def big_changes(table: pd.DataFrame) -> dict:
    """Variazioni grandi rispetto al mese prima, con le soglie del test (§2 e §12).
    Non fermano niente: vanno guardate a occhio nel rapporto."""
    out = {}
    for col in COLUMNS[1:]:
        values = list(table[col])
        flagged = []
        for prev_m, cur_m, a, b in zip(table["month"][:-1], table["month"][1:], values[:-1], values[1:]):
            change = b - a if col in b1.RATE_COLUMNS else b / a - 1
            if abs(change) > b1.BIG_CHANGE[col]:
                flagged.append({"month": cur_m, "change": float(change)})
        out[col] = flagged
    return out


def build(raw_dir: Path = RAW, now: datetime | None = None) -> tuple[pd.DataFrame, dict]:
    inputs = {col: latest_ecb_file(key, raw_dir) for col, key in ECB_SERIES.items()}
    inputs["gold_usd"] = latest_gold_file(raw_dir)
    hashes = {}
    for path in inputs.values():
        try:
            hashes[str(path)] = b1.verify_raw_file(path)
        except b1.DataCheckError as exc:
            raise PaperDataError(str(exc)) from exc

    series = {col: read_ecb(inputs[col], key, now) for col, key in ECB_SERIES.items()}
    series["gold_usd"] = read_gold(inputs["gold_usd"], now)
    table, last_by_series = assemble(series)

    report = {
        "start": PAPER_START,
        "first_month": table["month"].iloc[0],
        "last_month": table["month"].iloc[-1],
        "rows": len(table),
        "last_month_by_series": last_by_series,
        "big_changes": big_changes(table),
        "inputs_sha256": hashes,
    }
    return table, report


def main() -> None:
    table, report = build()
    OUTPUT_TABLE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_TABLE.write_bytes(b1.table_to_csv_bytes(table))
    report["output_table"] = str(OUTPUT_TABLE)
    report["output_table_sha256"] = sha256_file(OUTPUT_TABLE)
    OUTPUT_QUALITY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_QUALITY.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Tabella: {OUTPUT_TABLE} ({len(table)} mesi, {report['first_month']}..{report['last_month']})")
    print(f"Controlli: {OUTPUT_QUALITY}")
    flagged = {c: v for c, v in report["big_changes"].items() if v}
    if flagged:
        print(f"Attenzione, variazioni grandi da guardare: {flagged}")


if __name__ == "__main__":
    main()
