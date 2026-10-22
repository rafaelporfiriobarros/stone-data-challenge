
import csv
import json

import duckdb
import pytest

from stone_data_challenge.demo_pipeline import run_demo
from stone_data_challenge.synthetic_demo import (
    generate_synthetic_data,
)


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    output = tmp_path_factory.mktemp("stone_demo")
    report = run_demo(output, n_contracts=20, seed=42)
    return output, report


def test_synthetic_generator(tmp_path):
    paths = generate_synthetic_data(
        tmp_path,
        n_contracts=10,
    )

    assert all(path.exists() for path in paths.values())


def test_generator_is_deterministic(tmp_path):
    first = generate_synthetic_data(
        tmp_path / "first",
        n_contracts=10,
        seed=42,
    )

    second = generate_synthetic_data(
        tmp_path / "second",
        n_contracts=10,
        seed=42,
    )

    for key in first:
        assert first[key].read_bytes() == second[key].read_bytes()


def test_invalid_contract_count(tmp_path):
    with pytest.raises(ValueError):
        generate_synthetic_data(
            tmp_path,
            n_contracts=0,
        )


def test_pipeline_success(demo):
    _, report = demo

    assert report["status"] == "SUCCESS"
    assert report["data_type"] == "SYNTHETIC"


def test_contract_count(demo):
    _, report = demo

    assert report["contracts"] == 20


def test_payment_count(demo):
    _, report = demo

    assert report["payment_rows"] == 600


def test_reconciliation(demo):
    _, report = demo

    assert report["financial_reconciliation"] is True


def test_gold_file_exists(demo):
    output, _ = demo

    assert (
        output / "gold" / "contract_summary.parquet"
    ).exists()


def test_gold_unique_contracts(demo):
    output, _ = demo
    path = output / "gold" / "contract_summary.parquet"

    con = duckdb.connect()

    try:
        rows, unique_contracts = con.execute(
            """
            SELECT
                COUNT(*),
                COUNT(DISTINCT contrato_id)
            FROM read_parquet(?)
            """,
            [str(path)],
        ).fetchone()

        assert rows == unique_contracts == 20
    finally:
        con.close()


def test_no_negative_payments(demo):
    output, _ = demo
    path = output / "silver" / "payments.parquet"

    con = duckdb.connect()

    try:
        invalid = con.execute(
            """
            SELECT COUNT(*)
            FROM read_parquet(?)
            WHERE valor_pagamento < 0
            """,
            [str(path)],
        ).fetchone()[0]

        assert invalid == 0
    finally:
        con.close()


def test_report_saved(demo):
    output, report = demo

    saved = json.loads(
        (output / "demo_report.json").read_text(
            encoding="utf-8"
        )
    )

    assert saved == report


def test_campaigns_reference_valid_contracts(demo):
    output, _ = demo

    contracts_path = (
        output / "silver" / "contracts.parquet"
    )
    campaigns_path = (
        output / "silver" / "campaigns.parquet"
    )

    con = duckdb.connect()

    try:
        invalid = con.execute(
            """
            SELECT COUNT(*)
            FROM read_parquet(?) AS a
            LEFT JOIN read_parquet(?) AS c
                ON a.contrato_id = c.contrato_id
            WHERE c.contrato_id IS NULL
            """,
            [
                str(campaigns_path),
                str(contracts_path),
            ],
        ).fetchone()[0]

        assert invalid == 0
    finally:
        con.close()
