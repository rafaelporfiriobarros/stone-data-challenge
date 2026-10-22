
import json

import pytest

from stone_data_challenge.campaign_ablation import (
    EXPERIMENTS,
    MODEL_DIR,
    REPORT,
)


@pytest.fixture(scope="module")
def results():
    assert REPORT.exists()

    return json.loads(
        REPORT.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "name",
    EXPERIMENTS.keys(),
)
def test_model_saved(name):
    assert (
        MODEL_DIR / f"{name}.joblib"
    ).exists()


@pytest.mark.parametrize(
    "name",
    EXPERIMENTS.keys(),
)
def test_validation_metrics(results, name):
    metrics = results[name]["validation"]

    assert metrics["observacoes"] == 58863

    for metric in (
        "roc_auc",
        "pr_auc",
        "brier_score",
    ):
        assert 0 <= metrics[metric] <= 1

    assert metrics["log_loss"] >= 0


def test_incremental_metrics_exist(results):
    differences = results["incremental_effect"]

    assert set(differences) == {
        "roc_auc",
        "pr_auc",
        "brier_score",
        "log_loss",
    }


def test_feature_groups(results):
    financial = results[
        "financial_only"
    ]["features"]

    combined = results[
        "financial_plus_campaigns"
    ]["features"]

    assert len(financial) == 3
    assert len(combined) == 6
    assert set(financial).issubset(combined)
