"""Importazione dei file scaricati a mano: copia identica, nome unico,
SHA-256 controllato prima, tentativo registrato anche quando fallisce."""

from datetime import datetime, timezone
import json

import pytest

import src.import_manual as im
from src.hashing import sha256_file
from src.import_manual import import_file, METHOD


CONTENT = b"Date,Open,High,Low,Close\n2020-01-02,1,2,0.5,1.5\n2020-01-03,1.5,2,1,1.8\n"


def _make_original(tmp_path):
    original = tmp_path / "Manuale " / "xauusd_d.csv"
    original.parent.mkdir()
    original.write_bytes(CONTENT)
    return original


def test_import_copies_without_changes_and_writes_metadata(tmp_path):
    original = _make_original(tmp_path)
    expected = sha256_file(original)
    out = tmp_path / "raw" / "stooq"
    log = tmp_path / "logs" / "attempts.jsonl"

    meta = import_file(original, expected, "stooq", out, attempts_log=log)

    copied = out / f"{meta['acquisition_id']}.csv"
    assert copied.read_bytes() == CONTENT
    assert original.read_bytes() == CONTENT  # l'originale non è toccato

    saved = json.loads((out / f"{meta['acquisition_id']}.json").read_text(encoding="utf-8"))
    assert saved["sha256"] == expected
    assert saved["sha256_matches_original"] is True
    assert saved["file_size_bytes"] == len(CONTENT)
    assert saved["row_count"] == 2
    assert saved["method"] == METHOD == "manual_browser_download"
    assert saved["original_name"] == "xauusd_d.csv"
    assert saved["original_path"].endswith("Manuale /xauusd_d.csv")
    assert saved["original_modified_at"].endswith("+00:00")  # UTC
    assert saved["imported_at"].endswith("+00:00")

    entry = json.loads(log.read_text(encoding="utf-8").strip())
    assert entry["outcome"] == "SUCCESS"
    assert entry["source_id"] == "stooq"


def test_two_imports_get_different_names(tmp_path):
    original = _make_original(tmp_path)
    expected = sha256_file(original)
    out = tmp_path / "raw"
    log = tmp_path / "attempts.jsonl"

    m1 = import_file(original, expected, "stooq", out, attempts_log=log)
    m2 = import_file(original, expected, "stooq", out, attempts_log=log)

    assert m1["raw_file"] != m2["raw_file"]
    assert len(list(out.glob("*.csv"))) == 2


def test_wrong_sha256_stops_and_is_logged(tmp_path):
    original = _make_original(tmp_path)
    out = tmp_path / "raw"
    log = tmp_path / "attempts.jsonl"

    with pytest.raises(ValueError, match="SHA-256 diverso"):
        import_file(original, "0" * 64, "stooq", out, attempts_log=log)

    assert not out.exists() or list(out.iterdir()) == []

    entry = json.loads(log.read_text(encoding="utf-8").strip())
    assert entry["outcome"] == "FAILED"
    assert "SHA-256 diverso" in entry["error"]


def test_failure_after_check_is_logged_with_size(tmp_path, monkeypatch):
    # la copia fallisce dopo il controllo dell'impronta: tentativo FAILED con la dimensione
    original = _make_original(tmp_path)
    log = tmp_path / "attempts.jsonl"

    def broken_write(path, data):
        raise OSError("disco pieno (simulato)")

    monkeypatch.setattr(im, "write_exclusive", broken_write)
    with pytest.raises(OSError):
        import_file(original, sha256_file(original), "stooq", tmp_path / "raw", attempts_log=log)

    entry = json.loads(log.read_text(encoding="utf-8").strip())
    assert entry["outcome"] == "FAILED"
    assert entry["size_bytes"] == len(CONTENT)
    assert "disco pieno" in entry["error"]


# ------------------------------------------------------------------ aggiunte della revisione esterna


def test_import_never_overwrites_and_logs_size(tmp_path, monkeypatch):
    # stesso istante e stesso identificativo casuale -> stesso nome: la seconda copia deve fermarsi
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(im, "datetime", FixedDatetime)
    monkeypatch.setattr(im.uuid, "uuid4", lambda: im.uuid.UUID(int=0))
    original = _make_original(tmp_path)
    expected = sha256_file(original)
    out = tmp_path / "raw"
    log = tmp_path / "attempts.jsonl"

    meta = import_file(original, expected, "stooq", out, attempts_log=log)
    copied = out / f"{meta['acquisition_id']}.csv"
    copied.write_bytes(b"SEGNO")  # se il secondo import riscrive il file, il segno sparisce
    with pytest.raises(FileExistsError):
        import_file(original, expected, "stooq", out, attempts_log=log)

    assert copied.read_bytes() == b"SEGNO"  # mai sovrascritto
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert [e["outcome"] for e in entries] == ["SUCCESS", "FAILED"]
    assert entries[0]["size_bytes"] == len(CONTENT)
    assert entries[0]["script_version"] == im.IMPORTER_VERSION
    assert entries[0]["url"].startswith("file://")
