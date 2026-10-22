
import duckdb
import pytest

from stone_data_challenge.config import DATA_DIR


PATH = (
    DATA_DIR
    / "analytics"
    / "contrato_observacao_7d.parquet"
)


@pytest.fixture(scope="module")
def con():
    assert PATH.exists(), "Execute ml_dataset.py primeiro"
    connection = duckdb.connect()
    yield connection
    connection.close()


def test_dataset_not_empty(con):
    total = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(PATH)],
    ).fetchone()[0]

    assert total > 0


def test_unique_observations(con):
    total, distinct = con.execute(
        """
        SELECT
            COUNT(*),
            COUNT(DISTINCT (
                contrato_id,
                data_observacao
            ))
        FROM read_parquet(?)
        """,
        [str(PATH)],
    ).fetchone()

    assert total == distinct


def test_only_active_contracts(con):
    invalid = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE status_contrato <> 'Active'
           OR status_contrato IS NULL
        """,
        [str(PATH)],
    ).fetchone()[0]

    assert invalid == 0


def test_only_mondays(con):
    invalid = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE EXTRACT(ISODOW FROM data_observacao) <> 1
        """,
        [str(PATH)],
    ).fetchone()[0]

    assert invalid == 0


def test_valid_target(con):
    invalid = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE target_pagamento_7d NOT IN (0, 1)
           OR target_pagamento_7d IS NULL
        """,
        [str(PATH)],
    ).fetchone()[0]

    assert invalid == 0


def test_nonnegative_communication_counts(con):
    invalid = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE comunicacoes_7d < 0
           OR comunicacoes_30d < 0
           OR comunicacoes_7d > comunicacoes_30d
           OR emails_30d + hsm_30d <> comunicacoes_30d
           OR dias_com_acionamento_30d > 30
           OR comunicacoes_30d IS NULL
        """,
        [str(PATH)],
    ).fetchone()[0]

    assert invalid == 0
