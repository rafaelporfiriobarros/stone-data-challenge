
import csv

import pytest

from stone_data_challenge.campaign_eda_v2 import OUTPUT


def read_csv(filename):
    path = OUTPUT / filename

    assert path.exists(), f"Relatorio ausente: {filename}"

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


@pytest.mark.parametrize(
    "filename",
    [
        "payment_by_campaign_band.csv",
        "monthly_campaign_bands.csv",
        "yearly_campaign_bands.csv",
    ],
)
def test_report_exists_and_not_empty(filename):
    assert len(read_csv(filename)) > 0


def test_campaign_bands_reconcile():
    rows = read_csv("payment_by_campaign_band.csv")

    total = sum(
        int(row["observacoes"])
        for row in rows
    )

    assert total == 801725


def test_one_campaign_band_exists():
    rows = read_csv("payment_by_campaign_band.csv")

    one = next(
        row
        for row in rows
        if row["faixa_campanhas"] == "1"
    )

    assert int(one["observacoes"]) == 122670


def test_payment_rates_valid():
    rows = read_csv("monthly_campaign_bands.csv")

    for row in rows:
        rate = float(row["taxa_pagamento_pct"])

        assert 0 <= rate <= 100
