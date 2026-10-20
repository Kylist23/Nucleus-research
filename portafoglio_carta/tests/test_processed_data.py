import pandas as pd

from src.build_processed import build, DEFAULT_OUTPUT_FILE


def test_processed_file_exists():
    assert DEFAULT_OUTPUT_FILE.exists()


def test_processed_columns_and_missing_values_are_nan():
    df = pd.read_parquet(DEFAULT_OUTPUT_FILE)

    assert list(df.columns) == ["date", "ecb_rate", "h10_rate"]
    assert df["date"].is_monotonic_increasing
    assert df["date"].is_unique

    # i valori mancanti sono NaN, non zero
    assert (df["ecb_rate"] == 0).sum() == 0
    assert (df["h10_rate"] == 0).sum() == 0
    assert df["ecb_rate"].isna().sum() > 0
    assert df["h10_rate"].isna().sum() > 0


def test_build_is_reproducible(tmp_path):
    first = build()
    second = build()

    pd.testing.assert_frame_equal(first, second)

    first_file = tmp_path / "first.parquet"
    second_file = tmp_path / "second.parquet"
    first.to_parquet(first_file, index=False)
    second.to_parquet(second_file, index=False)

    # il contenuto letto è identico; i byte del file lo sono quasi sempre,
    # ma non è garantito dal formato Parquet, quindi non lo richiediamo
    pd.testing.assert_frame_equal(
        pd.read_parquet(first_file),
        pd.read_parquet(second_file),
    )
