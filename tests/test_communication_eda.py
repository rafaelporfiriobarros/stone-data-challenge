
import csv

import pytest

from stone_data_challenge.communication_eda import OUTPUT


@pytest.mark.parametrize(
    "filename",
    [
        "payment_by_communication_band.csv",
        "monthly_trends.csv",
        "communication_comparison.csv",
    ],
)
def test_eda_report_exists_and_has_data(filename):
    path = OUTPUT / filename

    assert path.exists(), f"Relatorio ausente: {filename}"

    with path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        rows = list(csv.DictReader(f))

    assert len(rows) > 0


def test_communication_band_rates():
    path = OUTPUT / "payment_by_communication_band.csv"

    with path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        rows = list(csv.DictReader(f))

    total = sum(int(row["observacoes"]) for row in rows)

    assert total == 801725

    for row in rows:
        rate = float(row["taxa_pagamento_pct"])
        assert 0 <= rate <= 100
