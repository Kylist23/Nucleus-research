from pathlib import Path
from datetime import datetime, timezone
import json

import pandas as pd

from src.h10_parsing import load_eur_series


ECB_FILE = Path("data/raw/ecb/eur_usd_ecb_raw.csv")
H10_FILE = Path(
    "data/raw/h10/h10_20260920T150631Z_3a34cb9c.csv"
)

OUTPUT_FILE = Path(
    "data/reports/cross_source/cross_source_ecb_h10_validation.json"
)


def main() -> None:
    ecb = pd.read_csv(ECB_FILE)

    h10_observations = load_eur_series(H10_FILE)
    h10 = pd.DataFrame(h10_observations, columns=["date", "h10"])

    ecb_data = ecb[
        ["TIME_PERIOD", "OBS_VALUE"]
    ].copy()

    ecb_data.columns = ["date", "ecb"]

    ecb_data["date"] = pd.to_datetime(
        ecb_data["date"]
    )

    h10["date"] = pd.to_datetime(
        h10["date"]
    )

    ecb_data["ecb"] = pd.to_numeric(
        ecb_data["ecb"],
        errors="coerce",
    )

    h10["h10"] = pd.to_numeric(
        h10["h10"],
        errors="coerce",
    )

    merged = (
        ecb_data
        .merge(
            h10,
            on="date",
            how="inner",
        )
        .dropna()
    )

    merged["diff"] = (
        merged["ecb"] - merged["h10"]
    )

    merged["abs_diff"] = merged["diff"].abs()

    abs_diff = merged["abs_diff"]

    large = merged[
        merged["abs_diff"] > 0.010
    ].copy()

    large["year"] = large["date"].dt.year

    top_10 = (
        merged
        .nlargest(10, "abs_diff")
        [
            [
                "date",
                "ecb",
                "h10",
                "diff",
                "abs_diff",
            ]
        ]
        .copy()
    )

    top_10["date"] = (
        top_10["date"]
        .dt.strftime("%Y-%m-%d")
    )

    report = {
        "validation_id": (
            "cross_source_ecb_h10"
        ),
        "generated_at_utc": (
            datetime.now(timezone.utc)
            .isoformat()
        ),
        "status": "COMPLETED",

        "sources": {
            "primary": {
                "source_id": "ecb",
                "series_id": (
                    "EXR.D.USD.EUR.SP00.A"
                ),
            },
            "secondary": {
                "source_id": (
                    "federal_reserve_h10"
                ),
                "series_id": (
                    "H10/H10/RXI$US_N.B.EU"
                ),
            },
        },

        "coverage": {
            "common_observations": len(
                merged
            ),
            "first_common_date": (
                merged["date"].min()
                .strftime("%Y-%m-%d")
            ),
            "last_common_date": (
                merged["date"].max()
                .strftime("%Y-%m-%d")
            ),
        },

        "difference_metrics": {
            "mean_difference_ecb_minus_h10": (
                float(merged["diff"].mean())
            ),
            "mean_absolute_difference": (
                float(abs_diff.mean())
            ),
            "minimum_difference": (
                float(merged["diff"].min())
            ),
            "maximum_difference": (
                float(merged["diff"].max())
            ),
            "maximum_absolute_difference": (
                float(abs_diff.max())
            ),
        },

        "distribution": {
            "identical": int(
                (abs_diff == 0).sum()
            ),
            "absolute_difference_le_0_001": int(
                (abs_diff <= 0.001).sum()
            ),
            "absolute_difference_le_0_005": int(
                (abs_diff <= 0.005).sum()
            ),
            "absolute_difference_le_0_010": int(
                (abs_diff <= 0.010).sum()
            ),
            "absolute_difference_gt_0_010": int(
                (abs_diff > 0.010).sum()
            ),
        },

        "large_difference_periods": {
            "threshold": 0.010,
            "observations": len(large),
            "years_involved": int(
                large["year"].nunique()
            ),
            "by_year": {
                str(year): int(count)
                for year, count
                in large.groupby("year").size().items()
            },
        },

        "top_10_absolute_differences": (
            top_10.to_dict(
                orient="records"
            )
        ),

        "interpretation": (
            "The two official reference-rate series "
            "are generally close but are not identical. "
            "Differences are preserved as descriptive "
            "cross-source validation evidence. "
            "This report does not classify either source "
            "as incorrect and does not define one source "
            "as an automatic fallback for the other."
        ),
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "Cross-source validation completed."
    )
    print(f"Report: {OUTPUT_FILE}")
    print(
        "Common observations:",
        report["coverage"]["common_observations"],
    )
    print(
        "Mean absolute difference:",
        report["difference_metrics"][
            "mean_absolute_difference"
        ],
    )


if __name__ == "__main__":
    main()
