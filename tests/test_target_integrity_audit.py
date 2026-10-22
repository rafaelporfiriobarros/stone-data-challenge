
import json

import pytest

from stone_data_challenge.target_integrity_audit import OUTPUT


@pytest.fixture(scope="module")
def report():
    path = OUTPUT / "target_integrity_report.json"

    assert path.exists()

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def test_report_exists(report):
    assert "evolucao_pagamentos" in report
    assert "comparacao_targets" in report


def test_disagreement_file_exists():
    assert (
        OUTPUT / "target_disagreements.csv"
    ).exists()


def test_snapshot_counts(report):
    data = report["evolucao_pagamentos"]

    assert data["snapshots"] > 0
    assert data["contratos"] > 0
    assert (
        data["snapshots_positivos"]
        <= data["snapshots"]
    )


def test_target_window_reconciliation(report):
    data = report["comparacao_targets"]

    assert (
        data["janelas_completas"]
        + data["janelas_incompletas"]
        == data["observacoes"]
    )


def test_disagreements_valid(report):
    data = report["comparacao_targets"]

    assert (
        data["divergencias_incremento"]
        <= data["janelas_completas"]
    )

    assert (
        data["divergencias_target_atual"]
        <= data["janelas_completas"]
    )


def test_target_rates_valid(report):
    data = report["comparacao_targets"]

    for name in (
        "taxa_target_atual",
        "taxa_target_incremento",
    ):
        value = data[name]

        assert value is not None
        assert 0 <= value <= 1
