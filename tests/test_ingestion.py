
import pytest
import duckdb

from stone_data_challenge.config import (
    BRONZE_DIR,
    DATASETS,
)


@pytest.mark.parametrize("name", DATASETS.keys())
def test_bronze_exists(name):
    path = BRONZE_DIR / f"{name}.parquet"

    assert path.exists(), (
        f"Parquet não encontrado: {path}"
    )


@pytest.mark.parametrize("name", DATASETS.keys())
def test_bronze_has_records(name):
    path = BRONZE_DIR / f"{name}.parquet"

    if not path.exists():
        pytest.fail(f"Execute a ingestão antes: {path}")

    con = duckdb.connect()

    try:
        total = con.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(path)],
        ).fetchone()[0]

        assert total > 0

    finally:
        con.close()
