
import csv
import json

import pytest

from stone_data_challenge.point_in_time_audit import OUTPUT


@pytest.fixture(scope="module")
def report():
    path = OUTPUT / "point_in_time_report.json"

    assert path.exists()

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def test_report_exists(report):
    assert "features" in report


def test_observations_exist(report):
    assert report["features"]["observacoes"] > 0


def test_unique_keys(report):
    metrics = report["features"]

    assert (
        metrics["observacoes"]
        == metrics["chaves_unicas"]
    )


def test_mismatch_counts_valid(report):
    metrics = report["features"]

    for key, value in metrics.items():
        if key.startswith("mismatch_"):
            assert 0 <= value <= metrics["observacoes"]


def test_missing_portfolio_valid(report):
    metrics = report["features"]

    assert (
        0 <= metrics["missing_portfolio"]
        <= metrics["observacoes"]
    )


def test_mismatch_csv_exists():
    path = OUTPUT / "feature_mismatches.csv"

    assert path.exists()

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.reader(file)
        header = next(reader)

    assert "contrato_id" in header


def test_temporal_boundaries(report):
    boundaries = report["fronteiras_temporais"]

    assert boundaries["embargo_days"] >= (
        boundaries["target_horizon_days"]
    )


def test_audit_period(report):
    assert report["periodo"]["inicio"] == "2022-01-10"
    assert report["periodo"]["fim"] == "2022-04-11"
