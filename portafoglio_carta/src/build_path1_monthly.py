"""Costruisce la tabella mensile della strada 1 (docs/STRADA1_SPEC_TEST.md, §1-§2).

- Legge solo file di data/raw/ il cui SHA-256 corrisponde ai metadati.
- Taglia ogni serie a 2022-12 SUBITO dopo la lettura, prima di qualsiasi calcolo
  (cassaforte: nessun dato dal 2023 in poi).
- Tutto è media del mese; oro e Bitcoin: media delle chiusure giornaliere.
- Un mese senza dati resta vuoto (NaN): mai zero, mai riempito.
- Scrive data/processed/path1_monthly.csv e data/reports/path1/quality_monthly.json.
  Rieseguendo con gli stessi file si ottengono file identici byte per byte.
"""

from pathlib import Path
import json
import math

import pandas as pd

from src.hashing import sha256_file


FIRST_MONTH = "1999-01"
LAST_MONTH = "2022-12"  # ultimo mese ammesso: dal 2023-01 in poi è cassaforte

RAW = Path("data/raw")
INPUTS = {
    "spx_usd": RAW / "ecb/ecb_20261013T160758Z_41acf924.csv",
    "sx5e_eur": RAW / "ecb/ecb_20261013T160800Z_8d48c957.csv",
    "y10_pct": RAW / "ecb/ecb_20261013T160803Z_0a873344.csv",
    "euribor3m_pct": RAW / "ecb/ecb_20261013T155500Z_a31be243.csv",
    "usd_per_eur": RAW / "ecb/ecb_20261013T160805Z_728c7c51.csv",
    "gold_usd": RAW / "stooq/stooq_xauusd_d_20261013T160751Z_94e017b4.csv",
    "btc_usd": RAW / "stooq/stooq_btcusd_d_20261013T160751Z_5d2e56cb.csv",
}
EXPECTED_KEYS = {
    "spx_usd": "FM.M.US.USD.DS.EI.S_PCOMP.HSTA",
    "sx5e_eur": "FM.M.U2.EUR.DS.EI.DJES50I.HSTA",
    "y10_pct": "IRS.M.I9.L.L40.CI.0000.EUR.N.Z",
    "euribor3m_pct": "FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA",
    "usd_per_eur": "EXR.M.USD.EUR.SP00.A",
}
DAILY_FX = RAW / "ecb/eur_usd_ecb_raw.csv"
DAILY_FX_METADATA = RAW / "ecb/eur_usd_ecb_acquisition.json"

# SHA-256 fissati nel codice (spec §12): se un file grezzo cambia, ci si ferma.
EXPECTED_SHA256 = {
    INPUTS["spx_usd"]: "990144517702b7500ebb4637ab2e5926573175ab873a28a67c032fe8d5ec44f8",
    INPUTS["sx5e_eur"]: "a90191aedea928e1b0c684006584c874d42a4e30312efdddb89f7e94fe5af90a",
    INPUTS["y10_pct"]: "34efcd7fca8e15c3f99bfb3ddfa6b36c9bac7805b7ef3f4da830f484cb2d0274",
    INPUTS["euribor3m_pct"]: "e9a64f4a48c7284e28c685aa7823bc98c7666bc78c835713659fe6e8d07529eb",
    INPUTS["usd_per_eur"]: "ed68895c12b7c08098c25b14c27473345832c2efd40d7fe815b66f7e6ad84f1a",
    INPUTS["gold_usd"]: "d17800fea4236b8d0c6cd4daff97ec02faa092378fcec065ddb74fb98fd12c5f",
    INPUTS["btc_usd"]: "f7d92c56a0d430696d0cb7ce2a3ca482cf6ef5d4c07215bc52791e6db54b9a98",
    DAILY_FX: "759544f2349d60ebb0583ac42d57b96dc53f25841fe90e7eeda6b0ed8cc3474d",
}

OUTPUT_TABLE = Path("data/processed/path1_monthly.csv")
OUTPUT_QUALITY = Path("data/reports/path1/quality_monthly.json")

COLUMNS = [
    "month", "spx_usd", "sx5e_eur", "y10_pct", "euribor3m_pct", "usd_per_eur",
    "gold_usd", "btc_usd", "spx_eur", "gold_eur", "btc_eur",
]

# Periodi in cui non può mancare nessun mese (spec §2)
REQUIRED_COMPLETE = {col: ("2001-01", LAST_MONTH) for col in COLUMNS[1:]}
REQUIRED_COMPLETE["btc_usd"] = ("2014-01", LAST_MONTH)
REQUIRED_COMPLETE["btc_eur"] = ("2014-01", LAST_MONTH)

BIG_CHANGE = {col: 0.30 for col in COLUMNS[1:]}
BIG_CHANGE["btc_usd"] = 0.60
BIG_CHANGE["btc_eur"] = 0.60
# §12: per i tassi la variazione si misura in punti percentuali assoluti, non in %
RATE_COLUMNS = {"y10_pct", "euribor3m_pct"}
BIG_CHANGE["y10_pct"] = 1.0
BIG_CHANGE["euribor3m_pct"] = 1.0

FX_MAX_DIFF = 0.0005


class DataCheckError(Exception):
    """Un controllo obbligatorio della spec non è passato: ci si ferma."""


def months_between(first: str, last: str) -> list[str]:
    """Tutti i mesi AAAA-MM da `first` a `last` compresi."""
    return [p.strftime("%Y-%m") for p in pd.period_range(first, last, freq="M")]


def verify_raw_file(path: Path, metadata_path: Path | None = None,
                    expected_sha256: str | None = None) -> str:
    """Controlla che lo SHA-256 del file sia quello scritto nei suoi metadati e,
    se dato, quello fissato nel codice."""
    if metadata_path is None:
        metadata_path = path.with_suffix(".json")
    in_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))["sha256"]
    actual = sha256_file(path)
    if actual != in_metadata:
        raise DataCheckError(f"SHA-256 di {path} diverso dai metadati: {actual} != {in_metadata}")
    if expected_sha256 is not None and actual != expected_sha256:
        raise DataCheckError(f"SHA-256 di {path} diverso da quello fissato: {actual} != {expected_sha256}")
    return actual


def _to_float(text: str) -> float:
    text = text.strip()
    return float(text) if text else math.nan


def read_ecb_monthly(path: Path, expected_key: str | None = None,
                     last_month: str = LAST_MONTH) -> pd.Series:
    """Serie mensile BCE (TIME_PERIOD AAAA-MM -> OBS_VALUE), tagliata a `last_month`."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    if expected_key is not None and set(raw["KEY"]) != {expected_key}:
        raise DataCheckError(f"{path}: chiave inattesa {set(raw['KEY'])}")
    raw = raw[raw["TIME_PERIOD"] <= last_month]  # taglio della cassaforte, prima di tutto
    if raw["TIME_PERIOD"].duplicated().any():
        raise DataCheckError(f"{path}: mesi duplicati")
    # §12: OBS_STATUS = A (valore normale) e COLLECTION = A (media del periodo)
    for col in ("OBS_STATUS", "COLLECTION"):
        if col not in raw.columns or set(raw[col]) - {"A"}:
            bad = sorted(set(raw[col]) - {"A"}) if col in raw.columns else "colonna assente"
            raise DataCheckError(f"{path}: {col} diverso da A fino a {last_month}: {bad}")
    values = [_to_float(v) for v in raw["OBS_VALUE"]]
    return pd.Series(values, index=list(raw["TIME_PERIOD"]), dtype="float64")


def read_daily_close(path: Path, last_month: str = LAST_MONTH,
                     date_col: str = "Date", value_col: str = "Close") -> pd.DataFrame:
    """Serie giornaliera (data, valore), tagliata a `last_month` compreso."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    raw = raw[raw[date_col].str[:7] <= last_month]  # taglio della cassaforte, prima di tutto
    if raw[date_col].duplicated().any():
        raise DataCheckError(f"{path}: date duplicate")
    return pd.DataFrame({
        "date": list(raw[date_col]),
        "value": [_to_float(v) for v in raw[value_col]],
    })


def monthly_mean(daily: pd.DataFrame) -> pd.Series:
    """Media aritmetica dei valori giornalieri per mese di calendario.
    I giorni senza valore sono ignorati; un mese senza nessun valore non compare."""
    d = daily.dropna(subset=["value"])
    month = d["date"].str[:7]
    return d.groupby(month)["value"].mean()


def assemble_table(series: dict[str, pd.Series], first: str = FIRST_MONTH,
                   last: str = LAST_MONTH) -> pd.DataFrame:
    """Mette insieme le serie mensili (indice AAAA-MM) in una riga per mese.
    I mesi senza dati restano NaN. Conversione in euro: prezzo_usd / usd_per_eur."""
    if last > LAST_MONTH:
        raise DataCheckError(f"Mese finale {last} oltre {LAST_MONTH}: cassaforte")
    months = months_between(first, last)
    table = pd.DataFrame({"month": months})
    for col in ["spx_usd", "sx5e_eur", "y10_pct", "euribor3m_pct", "usd_per_eur",
                "gold_usd", "btc_usd"]:
        s = series[col]
        table[col] = [float(s[m]) if m in s.index else math.nan for m in months]
    table["spx_eur"] = table["spx_usd"] / table["usd_per_eur"]
    table["gold_eur"] = table["gold_usd"] / table["usd_per_eur"]
    table["btc_eur"] = table["btc_usd"] / table["usd_per_eur"]
    return table[COLUMNS]


def quality_checks(table: pd.DataFrame, fx_daily_monthly: pd.Series) -> dict:
    """Controlli della spec §2. Solleva DataCheckError se manca un mese nei periodi
    usati o se il cambio mensile si discosta troppo dalla media dei giornalieri."""
    report = {"columns": {}, "missing_months": {}, "big_changes": {}, "fx_check": {}}
    t = table.set_index("month")

    if (t.index > LAST_MONTH).any():
        raise DataCheckError("La tabella contiene mesi dal 2023 in poi")

    for col in COLUMNS[1:]:
        s = t[col].dropna()
        report["columns"][col] = {
            "first_month": s.index[0] if len(s) else None,
            "last_month": s.index[-1] if len(s) else None,
            "min": float(s.min()) if len(s) else None,
            "max": float(s.max()) if len(s) else None,
        }

        first, last = REQUIRED_COMPLETE[col]
        missing = [m for m in months_between(first, last) if pd.isna(t.at[m, col])]
        report["missing_months"][col] = {"period": [first, last], "months": missing}

        # variazione rispetto al mese prima, solo tra mesi consecutivi con dati
        changes = []
        values = t[col]
        months = list(t.index)
        for prev, cur in zip(months[:-1], months[1:]):
            a, b = values[prev], values[cur]
            if pd.isna(a) or pd.isna(b):
                continue
            if col in RATE_COLUMNS:
                change = b - a  # punti percentuali
            elif a == 0:
                continue
            else:
                change = b / a - 1
            if abs(change) > BIG_CHANGE[col]:
                changes.append({"month": cur, "change": float(change)})
        report["big_changes"][col] = {
            "threshold": BIG_CHANGE[col],
            "unit": "percentage_points" if col in RATE_COLUMNS else "relative",
            "months": changes,
        }

    common = [m for m in t.index if m in fx_daily_monthly.index and not pd.isna(t.at[m, "usd_per_eur"])]
    diffs = {m: abs(float(fx_daily_monthly[m]) - float(t.at[m, "usd_per_eur"])) for m in common}
    worst = max(diffs, key=diffs.get) if diffs else None
    report["fx_check"] = {
        "months_compared": len(common),
        "max_abs_diff": diffs[worst] if worst else None,
        "max_abs_diff_month": worst,
        "threshold": FX_MAX_DIFF,
        "passed": bool(diffs) and diffs[worst] < FX_MAX_DIFF,
    }

    problems = {c: v["months"] for c, v in report["missing_months"].items() if v["months"]}
    if problems:
        raise DataCheckError(f"Mesi mancanti nei periodi usati: {problems}")
    if not report["fx_check"]["passed"]:
        raise DataCheckError(f"Controllo del cambio non passato: {report['fx_check']}")
    return report


def table_to_csv_bytes(table: pd.DataFrame) -> bytes:
    """CSV deterministico: stesso contenuto -> stessi byte."""
    return table.to_csv(index=False, lineterminator="\n").encode("utf-8")


def build(inputs: dict[str, Path] = INPUTS, daily_fx: Path = DAILY_FX,
          daily_fx_metadata: Path = DAILY_FX_METADATA,
          expected_sha256: dict = EXPECTED_SHA256) -> tuple[pd.DataFrame, dict]:
    input_hashes = {}
    for col, path in inputs.items():
        input_hashes[str(path)] = verify_raw_file(path, expected_sha256=expected_sha256[path])
    input_hashes[str(daily_fx)] = verify_raw_file(daily_fx, daily_fx_metadata,
                                                  expected_sha256=expected_sha256[daily_fx])

    series = {}
    for col in EXPECTED_KEYS:
        series[col] = read_ecb_monthly(inputs[col], EXPECTED_KEYS[col])
    series["gold_usd"] = monthly_mean(read_daily_close(inputs["gold_usd"]))
    series["btc_usd"] = monthly_mean(read_daily_close(inputs["btc_usd"]))

    table = assemble_table(series)

    fx_daily = read_daily_close(daily_fx, date_col="TIME_PERIOD", value_col="OBS_VALUE")
    report = quality_checks(table, monthly_mean(fx_daily))
    report["inputs_sha256"] = input_hashes
    report["first_month"] = table["month"].iloc[0]
    report["last_month"] = table["month"].iloc[-1]
    report["rows"] = len(table)
    return table, report


def main() -> None:
    table, report = build()
    data = table_to_csv_bytes(table)
    OUTPUT_TABLE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_TABLE.write_bytes(data)
    report["output_table"] = str(OUTPUT_TABLE)
    report["output_table_sha256"] = sha256_file(OUTPUT_TABLE)
    OUTPUT_QUALITY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_QUALITY.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Tabella: {OUTPUT_TABLE} ({len(table)} righe)")
    print(f"SHA-256: {report['output_table_sha256']}")
    print(f"Controlli: {OUTPUT_QUALITY}")


if __name__ == "__main__":
    main()
