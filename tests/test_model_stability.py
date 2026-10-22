
import csv

import pytest

from stone_data_challenge.model_stability import OUTPUT


FILES = [
    "stability_by_week.csv",
    "stability_by_campaign.csv",
    "stability_by_term.csv",
]


def read_report(filename):
    path = OUTPUT / filename
    assert path.exists()

    with path.open(
        encoding="utf-8-sig", newline=""
    ) as file:
        return list(csv.DictReader(file))


@pytest.mark.parametrize("filename", FILES)
def test_report_exists(filename):
    assert len(read_report(filename)) > 0


@pytest.mark.parametrize("filename", FILES)
def test_report_reconciles(filename):
    rows = read_report(filename)

    total = sum(
        int(row["observacoes"])
        for row in rows
    )

    assert total == 31570


@pytest.mark.parametrize("filename", FILES)
def test_report_metrics_valid(filename):
    for row in read_report(filename):
        observed = float(
            row["pagamento_observado_pct"]
        )
        predicted = float(
            row["probabilidade_prevista_pct"]
        )
        brier = float(row["brier_score"])

        assert 0 <= observed <= 100
        assert 0 <= predicted <= 100
        assert 0 <= brier <= 1
