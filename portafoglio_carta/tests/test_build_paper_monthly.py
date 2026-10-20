"""Tabella mensile del portafoglio di carta C: solo mesi della prova già finiti,
mai la cassaforte, nessun buco. Tutti i dati sono inventati e scritti in una cartella
temporanea: data/raw/ vero non viene toccato."""

from datetime import datetime, timezone
import hashlib
import json

import pandas as pd
import pytest

from src import build_paper_monthly as bpm
from src import paper_monthly
from src import path1_paper as paper


NOW = datetime(2027, 3, 10, tzinfo=timezone.utc)  # mese in corso: 2027-03
HEADER = "KEY,TIME_PERIOD,OBS_VALUE,OBS_STATUS,COLLECTION\n"


def _ecb_csv(key, rows):
    """rows: [(mese, valore, stato)]"""
    return HEADER + "".join(f"{key},{m},{v},{s},A\n" for m, v, s in rows)


def _write(raw, sub, name, text, meta):
    d = raw / sub
    d.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    (d / f"{name}.csv").write_bytes(data)
    meta = {**meta, "sha256": hashlib.sha256(data).hexdigest()}
    (d / f"{name}.json").write_text(json.dumps(meta), encoding="utf-8")
    return d / f"{name}.csv"


def _ecb(raw, col, rows, name=None, start=paper.PAPER_START, at="2027-03-05T10:00:00+00:00"):
    key = bpm.ECB_SERIES[col]
    return _write(raw, "ecb", name or f"ecb_{col}", _ecb_csv(key, rows),
                  {"series_id": key, "start_period_requested": start, "retrieved_at": at})


def _gold(raw, days, name="stooq_xauusd_d_x", at="2027-03-05T10:00:00+00:00"):
    text = "Date,Open,High,Low,Close\n" + "".join(f"{d},0,0,0,{v}\n" for d, v in days)
    return _write(raw, "stooq", name, text, {"imported_at": at})


def _all(raw, months=("2026-11", "2026-12", "2027-01", "2027-02"), skip=None):
    for col in bpm.ECB_SERIES:
        value = 1.25 if col == "usd_per_eur" else 100.0
        _ecb(raw, col, [(m, value, "A") for m in months if (col, m) != skip])
    _gold(raw, [(f"{m}-02", 2000.0) for m in months] + [(f"{m}-03", 2010.0) for m in months])


# ------------------------------------------------------------------ cassaforte e mese in corso

def test_vault_and_open_month_never_enter(tmp_path):
    _all(tmp_path)
    # righe della cassaforte con stato strano: se venissero lette, il controllo fallirebbe
    key = bpm.ECB_SERIES["spx_usd"]
    rows = [("2025-05", 1, "X"), ("2026-10", 1, "X")] + [
        (m, 100.0, "A") for m in ["2026-11", "2026-12", "2027-01", "2027-02"]] + [("2027-03", 1, "X")]
    _write(tmp_path, "ecb", "ecb_spx_usd", _ecb_csv(key, rows),
           {"series_id": key, "start_period_requested": paper.PAPER_START,
            "retrieved_at": "2027-03-05T10:00:00+00:00"})
    _gold(tmp_path, [("2024-01-02", 1.0), ("2026-10-30", 1.0), ("2026-11-02", 2000.0),
                     ("2026-12-02", 2000.0), ("2027-01-04", 2000.0), ("2027-02-01", 2000.0),
                     ("2027-03-01", 9999.0)])
    table, report = bpm.build(tmp_path, now=NOW)
    assert list(table["month"]) == ["2026-11", "2026-12", "2027-01", "2027-02"]
    assert table["gold_usd"].tolist() == [2000.0] * 4  # né 1,0 (cassaforte) né 9999 (mese in corso)
    assert report["first_month"] == paper.PAPER_START


def test_full_history_files_are_not_used(tmp_path):
    # i file del 13/10 hanno la storia completa (start_period_requested vuoto): non si usano
    for col in bpm.ECB_SERIES:
        _ecb(tmp_path, col, [("2026-11", 100.0, "A")], start=None)
    _gold(tmp_path, [("2026-11-02", 2000.0)])
    with pytest.raises(bpm.PaperDataError, match="a partire da"):
        bpm.build(tmp_path, now=NOW)


# ------------------------------------------------------------------ mesi e buchi

def test_table_stops_at_last_month_with_all_series(tmp_path):
    # la BCE non ha ancora pubblicato febbraio per l'Euribor: la tabella si ferma a gennaio
    _all(tmp_path, skip=("euribor3m_pct", "2027-02"))
    table, report = bpm.build(tmp_path, now=NOW)
    assert table["month"].iloc[-1] == "2027-01"
    assert report["last_month_by_series"]["euribor3m_pct"] == "2027-01"
    assert report["last_month_by_series"]["gold_usd"] == "2027-02"


def test_missing_month_in_the_middle_stops(tmp_path):
    _all(tmp_path, skip=("sx5e_eur", "2026-12"))
    with pytest.raises(bpm.PaperDataError, match="Mesi mancanti"):
        bpm.build(tmp_path, now=NOW)


def test_nothing_before_first_month_ends(tmp_path):
    # a novembre 2026 il mese d'acquisto non è finito: nessuna tabella
    _all(tmp_path, months=("2026-11",))
    with pytest.raises(bpm.PaperDataError, match="dopo la sua fine"):
        bpm.build(tmp_path, now=datetime(2026, 11, 20, tzinfo=timezone.utc))


def test_conversion_and_monthly_mean(tmp_path):
    _all(tmp_path)
    table, _ = bpm.build(tmp_path, now=NOW)
    # oro: media di 2000 e 2010 = 2005 dollari; 1 euro = 1,25 dollari -> 1604 euro
    assert table["gold_usd"].iloc[0] == pytest.approx(2005.0)
    assert table["gold_eur"].iloc[0] == pytest.approx(1604.0)
    assert table["spx_eur"].iloc[0] == pytest.approx(80.0)
    assert list(table.columns) == bpm.COLUMNS


def test_newest_download_wins(tmp_path):
    _all(tmp_path)
    _ecb(tmp_path, "spx_usd", [("2026-11", 100.0, "A"), ("2026-12", 110.0, "A"),
                               ("2027-01", 110.0, "A"), ("2027-02", 110.0, "A")],
         name="ecb_spx_new", at="2027-03-06T10:00:00+00:00")
    table, _ = bpm.build(tmp_path, now=NOW)
    assert table["spx_usd"].iloc[1] == 110.0


def test_changed_raw_file_stops(tmp_path):
    _all(tmp_path)
    path = tmp_path / "ecb" / "ecb_y10_pct.csv"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(bpm.PaperDataError, match="SHA-256"):
        bpm.build(tmp_path, now=NOW)


def test_table_feeds_paper_status(tmp_path):
    _all(tmp_path)
    table, _ = bpm.build(tmp_path, now=NOW)
    status = paper.paper_status(table, now=NOW)
    assert status["start"] == paper.PAPER_START
    assert status["months_of_returns"] == 3


# ------------------------------------------------------------------ aggiornamento mensile

def test_ecb_url_asks_only_from_first_month():
    url = paper_monthly.ecb_url("FM.M.US.USD.DS.EI.S_PCOMP.HSTA")
    assert url == ("https://data-api.ecb.europa.eu/service/data/FM/M.US.USD.DS.EI.S_PCOMP.HSTA"
                   f"?startPeriod={paper.PAPER_START}&format=csvdata")


class _Response:
    status_code = 200

    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


def test_monthly_download_and_import(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # registro dei tentativi in una cartella temporanea
    raw = tmp_path / "raw"

    def fake_fetch(url, timeout, headers):
        key = next(k for k in bpm.ECB_SERIES.values() if k.split(".", 1)[1] in url)
        return _Response(_ecb_csv(key, [("2026-11", 1.25, "A")]).encode())

    metas = paper_monthly.download_ecb(raw, fetch=fake_fetch)
    assert {m["start_period_requested"] for m in metas} == {paper.PAPER_START}

    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "xauusd_d.csv").write_text("Date,Open,High,Low,Close\n2026-11-02,0,0,0,2000\n")
    paper_monthly.import_gold(downloads / "xauusd_d.csv", raw)

    table, _ = bpm.build(raw, now=datetime(2026, 12, 5, tzinfo=timezone.utc))
    assert list(table["month"]) == ["2026-11"]


def test_old_gold_file_is_refused(tmp_path):
    # il file del mese prima, rimasto in Download, non deve essere importato per errore
    gold = tmp_path / "xauusd_d.csv"
    gold.write_text("Date,Close\n")
    later = datetime.fromtimestamp(gold.stat().st_mtime, tz=timezone.utc) + pd.Timedelta(days=10)
    with pytest.raises(ValueError, match="scarica di nuovo"):
        paper_monthly.import_gold(gold, tmp_path / "raw", now=later)
    assert not (tmp_path / "raw").exists()


def test_gold_file_name_is_checked(tmp_path):
    other = tmp_path / "gold.csv"
    other.write_text("Date,Close\n")
    with pytest.raises(ValueError, match="xauusd_d.csv"):
        paper_monthly.import_gold(other, tmp_path / "raw")
