"""Verifica le regole dei dati di CLAUDE.md: mai sovrascrivere, registrare
ogni tentativo anche quando fallisce, impronta SHA-256 nei metadati."""

from pathlib import Path
import json

import pytest

from src.exclusive_write import write_exclusive
from src.hashing import sha256_file
from src import acquire_ecb, acquire_h10


def test_exclusive_write_rejects_existing_file(tmp_path):
    target = tmp_path / "file.csv"

    write_exclusive(target, b"prima scrittura")

    with pytest.raises(FileExistsError):
        write_exclusive(target, b"seconda scrittura, non deve arrivare")

    assert target.read_bytes() == b"prima scrittura"


def _failing_fetch(*args, **kwargs):
    raise ConnectionError("rete non disponibile (simulata dal test)")


@pytest.mark.parametrize("module", [acquire_ecb, acquire_h10])
def test_failed_download_is_logged(tmp_path, module):
    output_dir = tmp_path / "raw"
    attempts_log = tmp_path / "logs" / "acquisition_attempts.jsonl"

    with pytest.raises(ConnectionError):
        module.run(
            output_dir=output_dir,
            attempts_log=attempts_log,
            fetch=_failing_fetch,
        )

    # nessun file dati creato
    assert not output_dir.exists() or list(output_dir.glob("*.csv")) == []

    # il tentativo fallito è registrato
    lines = attempts_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["outcome"] == "FAILED"
    assert "rete non disponibile" in entry["error"]
    assert entry["source_id"] == module.SOURCE_ID


CASES = [
    (
        Path("data/raw/ecb/eur_usd_ecb_raw.csv"),
        Path("data/raw/ecb/eur_usd_ecb_acquisition.json"),
    ),
    (
        Path("data/raw/h10/h10_20260920T150631Z_3a34cb9c.csv"),
        Path("data/raw/h10/h10_20260920T150631Z_3a34cb9c.json"),
    ),
]


@pytest.mark.parametrize("data_file,meta_file", CASES)
def test_sha256_matches_metadata(data_file, meta_file):
    expected_hash = json.loads(
        meta_file.read_text(encoding="utf-8")
    )["sha256"]

    assert sha256_file(data_file) == expected_hash


class _FakeResponse:
    status_code = 200
    content = b"KEY,TIME_PERIOD,OBS_VALUE\nX,2024-01,3.9\n"

    def raise_for_status(self):
        pass


def _fake_fetch(*args, **kwargs):
    return _FakeResponse()


def test_ecb_series_parameters_go_into_metadata(tmp_path):
    output_dir = tmp_path / "raw"
    attempts_log = tmp_path / "logs" / "acquisition_attempts.jsonl"

    metadata = acquire_ecb.run(
        output_dir=output_dir,
        attempts_log=attempts_log,
        url="https://example.test/ecb",
        fetch=_fake_fetch,
        series_id="FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA",
        description="Euribor 3 months, monthly average",
        start_period=None,
    )

    saved = json.loads(
        (output_dir / f"{metadata['acquisition_id']}.json").read_text(encoding="utf-8")
    )
    assert saved["series_id"] == "FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA"
    assert saved["description"] == "Euribor 3 months, monthly average"
    assert saved["start_period_requested"] is None
    assert saved["row_count"] == 1
    assert saved["sha256"] == sha256_file(Path(saved["raw_file"]))


def test_ecb_defaults_unchanged():
    assert acquire_ecb.SERIES_ID == "EXR.D.USD.EUR.SP00.A"
    assert acquire_ecb.DESCRIPTION == "Daily US dollar per euro exchange rate"
    assert acquire_ecb.START_PERIOD == "1999-01-04"


def test_ecb_failure_after_download_is_logged_with_size(tmp_path, monkeypatch):
    def broken_write(path, data):
        raise OSError("disco pieno (simulato)")

    monkeypatch.setattr(acquire_ecb, "write_exclusive", broken_write)
    log = tmp_path / "attempts.jsonl"
    with pytest.raises(OSError):
        acquire_ecb.run(output_dir=tmp_path / "raw", attempts_log=log, fetch=_fake_fetch)

    entry = json.loads(log.read_text(encoding="utf-8").strip())
    assert entry["outcome"] == "FAILED"
    assert entry["size_bytes"] == len(_FakeResponse.content)
    assert entry["http_status"] == 200
    assert entry["script_version"] == "nucleus-ecb-0.3"
