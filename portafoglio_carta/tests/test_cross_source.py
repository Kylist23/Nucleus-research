from pathlib import Path
import json


REPORT_FILE = Path(
    "data/reports/cross_source/cross_source_ecb_h10_validation.json"
)


def load_report():
    return json.loads(
        REPORT_FILE.read_text(
            encoding="utf-8"
        )
    )


def test_cross_source_report_exists():
    assert REPORT_FILE.exists()


def test_cross_source_status_is_completed():
    report = load_report()

    assert report["status"] == "COMPLETED"


def test_common_observations():
    report = load_report()

    assert (
        report["coverage"]["common_observations"]
        == 6854
    )


def test_common_coverage():
    report = load_report()

    assert (
        report["coverage"]["first_common_date"]
        == "1999-01-04"
    )

    assert (
        report["coverage"]["last_common_date"]
        == "2026-09-11"
    )


def test_difference_metrics():
    report = load_report()

    assert abs(
        report["difference_metrics"][
            "mean_absolute_difference"
        ] - 0.0029866647213306107
    ) < 1e-12


def test_large_difference_count():
    report = load_report()

    assert (
        report["distribution"][
            "absolute_difference_gt_0_010"
        ]
        == 230
    )


def test_large_difference_years():
    report = load_report()

    assert (
        report["large_difference_periods"][
            "years_involved"
        ]
        == 28
    )


def test_top_10_count():
    report = load_report()

    assert (
        len(
            report["top_10_absolute_differences"]
        )
        == 10
    )
