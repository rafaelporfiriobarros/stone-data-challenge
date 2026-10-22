
import json

import joblib
import pytest

from stone_data_challenge.calibrate_model import (
    CALIBRATOR_PATH,
    REPORT,
)


@pytest.fixture(scope="module")
def report():
    assert REPORT.exists()
    return json.loads(
        REPORT.read_text(encoding="utf-8")
    )


def test_calibrator_saved():
    assert CALIBRATOR_PATH.exists()
    model = joblib.load(CALIBRATOR_PATH)
    assert hasattr(model, "predict_proba")


def test_calibration_has_data(report):
    assert report["calibration_observations"] > 0
    assert report["check_observations"] > 0


@pytest.mark.parametrize("period", ["before", "after"])
def test_metrics_valid(report, period):
    metrics = report[period]

    assert 0 <= metrics["roc_auc"] <= 1
    assert 0 <= metrics["brier_score"] <= 1
    assert metrics["log_loss"] >= 0


def test_deltas_consistent(report):
    assert report["delta_brier"] == pytest.approx(
        report["after"]["brier_score"]
        - report["before"]["brier_score"]
    )
