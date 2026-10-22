
import duckdb
import pytest

from stone_data_challenge.config import DATA_DIR


PATH = (
    DATA_DIR
    / "analytics"
    / "contrato_observacao_7d_v2.parquet"
)


@pytest.fixture(scope="module")
def con():
    assert PATH.exists(), "Execute ml_dataset_v2.py"
    connection = duckdb.connect()
    yield connection
    connection.close()


def test_v2_preserves_observations(con):
    result = con.execute(
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

    assert result == (801725, 801725)


def test_v2_communication_hierarchy(con):
    invalid = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE campanhas_7d > campanhas_30d
           OR campanhas_30d >
              acionamentos_canal_30d
           OR acionamentos_canal_30d >
              registros_comunicacao_30d
           OR emails_30d + hsm_30d <>
              acionamentos_canal_30d
           OR dias_com_acionamento_30d > 30
           OR campanhas_30d < 0
        """,
        [str(PATH)],
    ).fetchone()[0]

    assert invalid == 0


def test_v2_preserves_original_counts(con):
    invalid = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE registros_comunicacao_30d <>
              registros_comunicacao_30d_original
        """,
        [str(PATH)],
    ).fetchone()[0]

    assert invalid == 0


def test_v2_preserves_target(con):
    original = (
        DATA_DIR
        / "analytics"
        / "contrato_observacao_7d.parquet"
    )

    changed = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?) AS v2
        JOIN read_parquet(?) AS v1
          ON v2.contrato_id = v1.contrato_id
         AND v2.data_observacao = v1.data_observacao
        WHERE v2.target_pagamento_7d <>
              v1.target_pagamento_7d
        """,
        [str(PATH), str(original)],
    ).fetchone()[0]

    assert changed == 0
