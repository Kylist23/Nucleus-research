"""Rapporto della strada 1: provato SOLO su una tabella inventata in una cartella temporanea."""

import json

import pytest

from src import path1_report
from src.hashing import sha256_file
from tests.test_path1_backtest import _fake_table


def _invented_table(tmp_path):
    p = tmp_path / "invented_monthly.csv"
    p.write_text(_fake_table("2008-01", "2016-12").to_csv(index=False, lineterminator="\n"),
                 encoding="utf-8")
    return p


def test_report_on_invented_table(tmp_path):
    table = _invented_table(tmp_path)
    out = tmp_path / "reports"
    kwargs = dict(period_long=("2008-01", "2016-12"), period_short=("2014-01", "2016-12"))

    p1 = path1_report.write_report(table, sha256_file(table), out, **kwargs)
    p2 = path1_report.write_report(table, sha256_file(table), out, **kwargs)

    assert p1 != p2  # nome unico, mai sovrascritto
    report = json.loads(p1.read_text(encoding="utf-8"))
    assert report["created_at_utc"].endswith("+00:00")
    assert len(report["code_commit"]) == 40
    assert len(report["spec_commit"]) == 40
    assert isinstance(report["uncommitted_changes"], bool)
    assert report["table_sha256"] == sha256_file(table)
    assert report["measures"]["periods"]["long"]["portfolios"]["A"]["evaluation"]["steps"] == 107
    assert "final_winner" in report["measures"]["verdict"]


def test_report_refuses_wrong_table_hash(tmp_path):
    table = _invented_table(tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        path1_report.write_report(table, "0" * 64, tmp_path / "reports")
    assert not (tmp_path / "reports").exists()


def test_report_defaults_point_to_the_real_table():
    # solo i nomi: il rapporto sui dati veri non si esegue in questa fase
    assert str(path1_report.TABLE) == "data/processed/path1_monthly.csv"
    assert path1_report.TABLE_SHA256 == (
        "55fbfc19df2164bb7d85a4063436a240c3842053e5c5b8f7007f9117228fcf90"
    )
