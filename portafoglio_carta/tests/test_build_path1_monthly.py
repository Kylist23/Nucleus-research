"""Tabella mensile della strada 1 (spec §2): medie mensili, conversione in euro,
mesi vuoti lasciati vuoti, taglio della cassaforte, controlli di qualità."""

import hashlib
import json
import math

import pandas as pd
import pytest

from src import build_path1_monthly as b
from src.hashing import sha256_file


def _series(d):
    return pd.Series(d, dtype="float64")


def test_monthly_mean_leaves_empty_month_missing():
    # gennaio: 10 e 20 -> media 15; febbraio: nessun dato; marzo: un valore vuoto e 9
    daily = pd.DataFrame({
        "date": ["2020-01-02", "2020-01-03", "2020-03-02", "2020-03-03"],
        "value": [10.0, 20.0, math.nan, 9.0],
    })
    means = b.monthly_mean(daily)
    assert means["2020-01"] == 15.0
    assert "2020-02" not in means.index
    assert means["2020-03"] == 9.0

    table = b.assemble_table(
        {
            "spx_usd": _series({}), "sx5e_eur": _series({}), "y10_pct": _series({}),
            "euribor3m_pct": _series({}), "usd_per_eur": _series({"2020-01": 1.0}),
            "gold_usd": means, "btc_usd": _series({}),
        },
        first="2020-01", last="2020-03",
    )
    assert list(table["month"]) == ["2020-01", "2020-02", "2020-03"]
    assert table["gold_usd"].iloc[0] == 15.0
    assert math.isnan(table["gold_usd"].iloc[1])  # vuoto, mai zero
    assert math.isnan(table["gold_usd"].iloc[2]) is False


def test_conversion_to_eur():
    # 1 euro = 1,25 dollari: 100 dollari = 80 euro; 50 dollari = 40 euro
    months = {"2020-01": 1.25}
    table = b.assemble_table(
        {
            "spx_usd": _series({"2020-01": 100.0}), "sx5e_eur": _series({}),
            "y10_pct": _series({}), "euribor3m_pct": _series({}),
            "usd_per_eur": _series(months), "gold_usd": _series({"2020-01": 50.0}),
            "btc_usd": _series({"2020-01": 1000.0}),
        },
        first="2020-01", last="2020-01",
    )
    assert table["spx_eur"].iloc[0] == pytest.approx(80.0)
    assert table["gold_eur"].iloc[0] == pytest.approx(40.0)
    assert table["btc_eur"].iloc[0] == pytest.approx(800.0)
    assert list(table.columns) == b.COLUMNS


def test_vault_cut_happens_when_reading(tmp_path):
    ecb = tmp_path / "ecb.csv"
    ecb.write_text(
        "KEY,TIME_PERIOD,OBS_VALUE,OBS_STATUS,COLLECTION\n"
        "K,2022-11,1,A,A\nK,2022-12,2,A,A\nK,2023-01,3,P,E\n", encoding="utf-8"
    )
    s = b.read_ecb_monthly(ecb, "K")
    assert list(s.index) == ["2022-11", "2022-12"]

    daily = tmp_path / "d.csv"
    daily.write_text(
        "Date,Open,High,Low,Close\n2022-12-30,1,1,1,5\n2023-01-02,1,1,1,7\n", encoding="utf-8"
    )
    d = b.read_daily_close(daily)
    assert list(d["date"]) == ["2022-12-30"]

    with pytest.raises(b.DataCheckError):
        b.assemble_table({}, first="2022-12", last="2023-01")


def _full_table(first="1999-01", last="2022-12"):
    months = b.months_between(first, last)
    n = len(months)
    t = pd.DataFrame({"month": months})
    for col in b.COLUMNS[1:]:
        t[col] = [100.0] * n
    return t


def test_quality_passes_and_lists_big_changes():
    t = _full_table()
    i = t.index[t["month"] == "2010-05"][0]
    t.loc[i, "gold_usd"] = 140.0  # +40%: elencato (soglia 30%), non tolto
    t.loc[i, "btc_usd"] = 150.0   # +50%: sotto la soglia del Bitcoin (60%)
    fx = pd.Series(100.0, index=t["month"])
    report = b.quality_checks(t, fx)
    # 2010-05: 100 -> 140 = +40% (elencato); 2010-06: 140 -> 100 = -28,6% (sotto il 30%)
    assert report["big_changes"]["gold_usd"]["months"] == [
        {"month": "2010-05", "change": pytest.approx(0.4)},
    ]
    assert report["big_changes"]["btc_usd"]["months"] == []
    assert report["fx_check"]["passed"] is True
    assert t.loc[i, "gold_usd"] == 140.0


def test_quality_stops_on_missing_month():
    t = _full_table()
    t.loc[t["month"] == "2005-03", "spx_usd"] = math.nan
    with pytest.raises(b.DataCheckError, match="Mesi mancanti"):
        b.quality_checks(t, pd.Series(100.0, index=t["month"]))


def test_quality_allows_bitcoin_missing_before_2014():
    t = _full_table()
    t.loc[t["month"] < "2014-01", ["btc_usd", "btc_eur"]] = math.nan
    report = b.quality_checks(t, pd.Series(100.0, index=t["month"]))
    assert report["columns"]["btc_usd"]["first_month"] == "2014-01"


def test_quality_stops_on_fx_difference():
    t = _full_table()
    # differenza |0,0005 - 0,0| = 0,0005 esatta: non è "sotto" la soglia -> stop
    t.loc[t["month"] == "2008-07", "usd_per_eur"] = 0.0005
    fx = pd.Series(100.0, index=t["month"])
    fx["2008-07"] = 0.0
    with pytest.raises(b.DataCheckError, match="cambio"):
        b.quality_checks(t, fx)
    # differenza 0,00049 (sotto la soglia): passa
    fx["2008-07"] = 0.00001
    assert b.quality_checks(t, fx)["fx_check"]["passed"] is True


def test_rebuild_from_raw_files_gives_the_committed_table():
    # ricostruisce dai file di data/raw (senza scrivere niente) e confronta l'impronta
    table, report = b.build()
    data = b.table_to_csv_bytes(table)
    assert hashlib.sha256(data).hexdigest() == (
        "55fbfc19df2164bb7d85a4063436a240c3842053e5c5b8f7007f9117228fcf90"
    )
    assert table["month"].iloc[-1] == "2022-12"
    assert report["last_month"] == "2022-12"
    assert b"\r" not in data


def test_ecb_status_must_be_a(tmp_path):
    ecb = tmp_path / "ecb.csv"
    # 2023: stato diverso, ma è dopo il taglio -> ignorato
    ecb.write_text("KEY,TIME_PERIOD,OBS_VALUE,OBS_STATUS,COLLECTION\n"
                   "K,2022-12,2,A,A\nK,2023-01,3,P,E\n", encoding="utf-8")
    assert list(b.read_ecb_monthly(ecb, "K").index) == ["2022-12"]
    # stato provvisorio prima del taglio -> stop
    ecb.write_text("KEY,TIME_PERIOD,OBS_VALUE,OBS_STATUS,COLLECTION\n"
                   "K,2022-11,1,P,A\nK,2022-12,2,A,A\n", encoding="utf-8")
    with pytest.raises(b.DataCheckError, match="OBS_STATUS"):
        b.read_ecb_monthly(ecb, "K")
    # fine periodo invece di media -> stop
    ecb.write_text("KEY,TIME_PERIOD,OBS_VALUE,OBS_STATUS,COLLECTION\n"
                   "K,2022-12,2,A,E\n", encoding="utf-8")
    with pytest.raises(b.DataCheckError, match="COLLECTION"):
        b.read_ecb_monthly(ecb, "K")


def test_pinned_sha256_mismatch_stops(tmp_path):
    f = tmp_path / "x.csv"
    f.write_bytes(b"abc")
    meta = tmp_path / "x.json"
    meta.write_text(json.dumps({"sha256": sha256_file(f)}), encoding="utf-8")
    assert b.verify_raw_file(f, meta, expected_sha256=sha256_file(f)) == sha256_file(f)
    with pytest.raises(b.DataCheckError, match="fissato"):
        b.verify_raw_file(f, meta, expected_sha256="0" * 64)


def test_all_raw_hashes_are_pinned():
    assert set(b.EXPECTED_SHA256) == set(b.INPUTS.values()) | {b.DAILY_FX}


def test_rates_big_change_is_in_absolute_points():
    # 10 anni: da 0,05% a 0,50% = +900% ma solo +0,45 punti -> non elencato
    #          da 0,50% a 1,60% = +1,10 punti -> elencato
    #          da 1,60% a 0,60% = -1,00 punti esatti -> non elencato (serve "oltre")
    t = _full_table()
    for m, v in [("2015-01", 0.05), ("2015-02", 0.5), ("2015-03", 1.6), ("2015-04", 0.6)]:
        t.loc[t["month"] == m, "y10_pct"] = v
    t.loc[t["month"] == "2015-05", "y10_pct"] = 100.0  # torna a 100: +99,4 punti
    report = b.quality_checks(t, pd.Series(100.0, index=t["month"]))
    listed = report["big_changes"]["y10_pct"]
    assert listed["unit"] == "percentage_points"
    assert [x["month"] for x in listed["months"]] == ["2015-01", "2015-03", "2015-05"]
    assert listed["months"][1]["change"] == pytest.approx(1.1)
    assert report["big_changes"]["spx_usd"]["unit"] == "relative"


# ------------------------------------------------------------------ aggiunte della revisione esterna


def test_monthly_mean_is_arithmetic_mean():
    # (10 + 20 + 60) / 3 = 30; la mediana sarebbe 20
    daily = pd.DataFrame({"date": ["2020-01-02", "2020-01-03", "2020-01-06"],
                          "value": [10.0, 20.0, 60.0]})
    assert b.monthly_mean(daily)["2020-01"] == pytest.approx(30.0)


def test_empty_values_are_read_as_missing(tmp_path):
    ecb = tmp_path / "ecb.csv"
    ecb.write_text("KEY,TIME_PERIOD,OBS_VALUE,OBS_STATUS,COLLECTION\n"
                   "K,2020-01,1.5,A,A\nK,2020-02,,A,A\n", encoding="utf-8")
    s = b.read_ecb_monthly(ecb, "K")
    assert s["2020-01"] == 1.5
    assert math.isnan(s["2020-02"])          # vuoto, mai zero
    daily = tmp_path / "d.csv"
    daily.write_text("Date,Open,High,Low,Close\n2020-01-02,1,1,1,4\n2020-01-03,1,1,1,\n",
                     encoding="utf-8")
    # il giorno vuoto non conta: media 4 (contato come zero sarebbe 2)
    assert b.monthly_mean(b.read_daily_close(daily))["2020-01"] == 4.0


def test_raw_file_sha_and_series_key_are_checked(tmp_path):
    f = tmp_path / "x.csv"
    f.write_bytes(b"KEY,TIME_PERIOD,OBS_VALUE\nK,2020-01,1\n")
    meta = tmp_path / "x.json"
    meta.write_text(json.dumps({"sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(b.DataCheckError, match="SHA-256"):
        b.verify_raw_file(f)
    meta.write_text(json.dumps({"sha256": sha256_file(f)}), encoding="utf-8")
    assert b.verify_raw_file(f) == sha256_file(f)
    with pytest.raises(b.DataCheckError, match="chiave"):
        b.read_ecb_monthly(f, "ALTRA.CHIAVE")


def test_fx_difference_exactly_at_threshold_stops():
    # |0,0 - 0,0005| = 0,0005 esatto (100,0005 - 100 invece fa 0,0005000000000024)
    t = _full_table()
    t.loc[t["month"] == "2008-07", "usd_per_eur"] = 0.0005
    fx = pd.Series(100.0, index=t["month"])
    fx["2008-07"] = 0.0
    with pytest.raises(b.DataCheckError, match="cambio"):
        b.quality_checks(t, fx)


def test_quality_stops_on_missing_first_or_last_required_month():
    for month, col in [("2001-01", "y10_pct"), ("2022-12", "gold_usd"), ("2014-01", "btc_eur")]:
        t = _full_table()
        t.loc[t["month"] == month, col] = math.nan
        with pytest.raises(b.DataCheckError, match="Mesi mancanti"):
            b.quality_checks(t, pd.Series(100.0, index=t["month"]))


def test_quality_btc_eur_uses_60_percent_threshold():
    t = _full_table()
    t.loc[t["month"] == "2016-05", "btc_eur"] = 150.0   # +50%: sotto il 60% del Bitcoin
    report = b.quality_checks(t, pd.Series(100.0, index=t["month"]))
    assert report["big_changes"]["btc_eur"]["months"] == []


def test_quality_refuses_vault_months():
    t = _full_table("1999-01", "2023-01")
    with pytest.raises(b.DataCheckError, match="2023"):
        b.quality_checks(t, pd.Series(100.0, index=t["month"]))


def test_csv_bytes_exact_and_empty_month_written_empty():
    t = pd.DataFrame({"month": ["2020-01", "2020-02"], "spx_usd": [1.5, math.nan]})
    assert b.table_to_csv_bytes(t) == b"month,spx_usd\n2020-01,1.5\n2020-02,\n"




def test_rates_rule_also_applies_to_euribor():
    # Euribor vicino a zero: da 0,10% a 0,25% = +150% ma solo +0,15 punti -> non elencato
    #                        da 0,25% a 1,50% = +1,25 punti -> elencato
    t = _full_table()
    t["euribor3m_pct"] = 0.10
    t.loc[t["month"] == "2015-03", "euribor3m_pct"] = 0.25
    t.loc[t["month"] >= "2015-04", "euribor3m_pct"] = 1.50
    report = b.quality_checks(t, pd.Series(100.0, index=t["month"]))
    listed = report["big_changes"]["euribor3m_pct"]
    assert listed["unit"] == "percentage_points"
    assert [x["month"] for x in listed["months"]] == ["2015-04"]
    assert listed["months"][0]["change"] == pytest.approx(1.25)
