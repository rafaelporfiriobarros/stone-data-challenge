
import json

import duckdb
import pytest

from stone_data_challenge.final_evaluation import (
    OUTPUT,
)


@pytest.fixture(scope="module")
def report():
    path = OUTPUT / "final_metrics.json"

    assert path.exists()

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


@pytest.mark.parametrize(
    "filename",
    [
        "predictions.parquet",
        "payment_by_decile.csv",
        "calibration_by_band.csv",
        "final_metrics.json",
    ],
)
def test_output_exists(filename):
    assert (
        OUTPUT / filename
    ).exists()


def test_expected_test_size(report):
    assert (
        report["after_calibration"][
            "observacoes"
        ]
        == 31570
    )


def test_probabilities_valid():
    con = duckdb.connect()

    try:
        invalid = con.execute(
            """
            SELECT COUNT(*)
            FROM read_parquet(?)
            WHERE probability_calibrated
                NOT BETWEEN 0 AND 1
               OR probability_calibrated IS NULL
            """,
            [
                str(
                    OUTPUT
                    / "predictions.parquet"
                )
            ],
        ).fetchone()[0]
    finally:
        con.close()

    assert invalid == 0


def test_decile_reconciliation():
    con = duckdb.connect()

    try:
        result = con.execute(
            """
            SELECT
                COUNT(*) AS groups,
                SUM(observacoes) AS total
            FROM read_csv_auto(?)
            """,
            [
                str(
                    OUTPUT
                    / "payment_by_decile.csv"
                )
            ],
        ).fetchone()
    finally:
        con.close()

    assert result == (10, 31570)


def test_calibration_metrics_valid(report):
    for name in (
        "before_calibration",
        "after_calibration",
    ):
        metrics = report[name]

        assert 0 <= metrics["roc_auc"] <= 1
        assert 0 <= metrics["pr_auc"] <= 1
        assert 0 <= metrics["brier_score"] <= 1
        assert metrics["log_loss"] >= 0
