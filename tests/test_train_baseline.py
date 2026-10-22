
import json

import joblib
import pytest

from stone_data_challenge.train_baseline import (
    FEATURES,
    MODEL_DIR,
    REPORT_PATH,
)


@pytest.fixture(scope="module")
def report():
    assert REPORT_PATH.exists()
    return json.loads(
        REPORT_PATH.read_text(encoding="utf-8")
    )


def test_feature_list(report):
    assert report["features"] == FEATURES
    assert "target_pagamento_7d" not in FEATURES
    assert "contrato_id" not in FEATURES
    assert "nr_documento" not in FEATURES


@pytest.mark.parametrize(
    "name",
    ["dummy", "logistic_regression"],
)
def test_model_saved(name):
    path = MODEL_DIR / f"{name}.joblib"

    assert path.exists()
    assert hasattr(joblib.load(path), "predict_proba")


@pytest.mark.parametrize(
    "name",
    ["dummy", "logistic_regression"],
)
def test_metrics_valid(report, name):
    for split in ("train", "validation", "test"):
        metrics = report["models"][name][split]

        assert metrics["observacoes"] > 0

        for metric in (
            "roc_auc",
            "pr_auc",
            "balanced_accuracy",
            "brier_score",
        ):
            value = metrics[metric]
            assert value is not None
            assert 0 <= value <= 1


def test_expected_test_size(report):
    for model in report["models"].values():
        assert model["test"]["observacoes"] == 31570
