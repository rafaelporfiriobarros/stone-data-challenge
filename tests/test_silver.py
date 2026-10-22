
import duckdb
import pytest

from stone_data_challenge.config import (
    BRONZE_DIR,
    DATA_DIR,
    DATASETS,
)

SILVER_DIR = DATA_DIR / "silver"
QUARANTINE_DIR = DATA_DIR / "quarantine"


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect()
    yield connection
    connection.close()


@pytest.mark.parametrize("name", DATASETS.keys())
def test_silver_reconciliation(con, name):
    bronze = BRONZE_DIR / f"{name}.parquet"
    silver = SILVER_DIR / f"{name}.parquet"
    quarantine = QUARANTINE_DIR / f"{name}.parquet"

    assert silver.exists()
    assert quarantine.exists()

    bronze_count = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(bronze)],
    ).fetchone()[0]

    silver_count = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(silver)],
    ).fetchone()[0]

    quarantine_count = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(quarantine)],
    ).fetchone()[0]

    assert bronze_count == silver_count + quarantine_count


def test_safra_is_date(con):
    path = SILVER_DIR / "portfolio_geral.parquet"

    result = con.execute(
        """
        DESCRIBE SELECT safra
        FROM read_parquet(?)
        """,
        [str(path)],
    ).fetchone()

    assert result[1] == "DATE"


def test_safra_is_first_day_of_month(con):
    path = SILVER_DIR / "portfolio_geral.parquet"

    invalid = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE EXTRACT(DAY FROM safra) != 1
           OR safra IS NULL
        """,
        [str(path)],
    ).fetchone()[0]

    assert invalid == 0


def test_tpv_date_type(con):
    path = SILVER_DIR / "portfolio_tpv.parquet"

    result = con.execute(
        """
        DESCRIBE SELECT dt_transacao
        FROM read_parquet(?)
        """,
        [str(path)],
    ).fetchone()

    assert result[1] == "DATE"


def test_financial_value_type(con):
    path = SILVER_DIR / "portfolio_geral.parquet"

    result = con.execute(
        """
        DESCRIBE SELECT vlr_saldo_devedor
        FROM read_parquet(?)
        """,
        [str(path)],
    ).fetchone()

    assert result[1].startswith("DECIMAL")
