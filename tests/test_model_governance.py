
import json

import pytest

from stone_data_challenge.model_governance import OUTPUT


@pytest.fixture(scope="module")
def report():
    path = OUTPUT / "model_governance_report.json"

    assert path.exists()

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def test_json_report_exists(report):
    assert report["project"] == "Stone Data Challenge"


def test_markdown_report_exists():
    path = OUTPUT / "model_governance_report.md"

    assert path.exists()
    assert path.stat().st_size > 0


def test_model_status(report):
    assert report["model_status"] == "EXPERIMENTAL"


def test_splits_exist(report):
    assert set(report["splits"]) == {
        "train",
        "validation",
        "test",
    }


def test_test_reconciliation(report):
    assert (
        report["splits"]["test"]["observations"]
        == report["predictions"]["observations"]
    )


def test_prediction_keys_unique(report):
    predictions = report["predictions"]

    assert (
        predictions["observations"]
        == predictions["unique_keys"]
    )


def test_prediction_metrics(report):
    predictions = report["predictions"]

    assert 0 <= predictions["observed_rate"] <= 1
    assert 0 <= predictions["predicted_rate"] <= 1
    assert 0 <= predictions["brier_score"] <= 1


def test_features_documented(report):
    assert len(report["features"]) == 6


def test_audits_included(report):
    assert "target_integrity" in report["audits"]
    assert "point_in_time" in report["audits"]


def test_risks_documented(report):
    risks = report["risks"]

    assert len(risks) >= 4
    assert all(
        risk["status"] == "OPEN"
        for risk in risks
    )
