
import duckdb
import pytest

from stone_data_challenge.config import DATA_DIR


GOLD = DATA_DIR / "gold"


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect()
    yield connection
    connection.close()


@pytest.mark.parametrize(
    "name,expected",
    [
        ("dim_clientes", 14265),
        ("dim_contratos", 14756),
        ("fact_contrato_diario", 8061006),
        ("fact_comunicacoes", 403740),
        ("fact_tpv_diario", 4408597),
    ],
)
def test_gold_counts(con, name, expected):
    path = GOLD / f"{name}.parquet"
    assert path.exists()

    result = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(path)],
    ).fetchone()[0]

    assert result == expected


@pytest.mark.parametrize(
    "name,key",
    [
        ("dim_clientes", "nr_documento"),
        ("dim_contratos", "contrato_id"),
        (
            "fact_contrato_diario",
            "contrato_id, dt_ref_portfolio",
        ),
        (
            "fact_tpv_diario",
            "nr_documento, dt_transacao",
        ),
        ("fact_comunicacoes", "comunicacao_sk"),
    ],
)
def test_gold_unique_keys(con, name, key):
    path = GOLD / f"{name}.parquet"

    total, unique = con.execute(
        f"""
        SELECT
            COUNT(*),
            COUNT(DISTINCT ({key}))
        FROM read_parquet(?)
        """,
        [str(path)],
    ).fetchone()

    assert total == unique


def test_client_conflict_count(con):
    path = GOLD / "dim_clientes.parquet"

    count = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE cadastro_conflitante
        """,
        [str(path)],
    ).fetchone()[0]

    assert count == 114


def test_communication_status_preserved(con):
    path = GOLD / "fact_comunicacoes.parquet"

    result = con.execute(
        """
        SELECT
            COUNT(*),
            COUNT(*) FILTER (
                WHERE status = 'RESPONDIDO'
            )
        FROM read_parquet(?)
        """,
        [str(path)],
    ).fetchone()

    assert result == (403740, 3202)
