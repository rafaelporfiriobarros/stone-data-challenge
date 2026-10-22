
import duckdb
import pytest

from stone_data_challenge.temporal_split import (
    OUTPUT,
    SPLITS,
)


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect()
    yield connection
    connection.close()


@pytest.mark.parametrize("name", SPLITS.keys())
def test_split_exists_and_has_data(con, name):
    path = OUTPUT / f"{name}.parquet"

    assert path.exists()

    count = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(path)],
    ).fetchone()[0]

    assert count > 0


@pytest.mark.parametrize(
    "name,start,end",
    [
        (name, dates[0], dates[1])
        for name, dates in SPLITS.items()
    ],
)
def test_split_dates(con, name, start, end):
    path = OUTPUT / f"{name}.parquet"

    invalid = con.execute(
        """
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE data_observacao < CAST(? AS DATE)
           OR data_observacao > CAST(? AS DATE)
        """,
        [str(path), start, end],
    ).fetchone()[0]

    assert invalid == 0


def test_no_overlapping_observation_keys(con):
    paths = [
        str(OUTPUT / f"{name}.parquet")
        for name in SPLITS
    ]

    duplicates = con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                contrato_id,
                data_observacao
            FROM read_parquet(?)

            UNION ALL

            SELECT
                contrato_id,
                data_observacao
            FROM read_parquet(?)

            UNION ALL

            SELECT
                contrato_id,
                data_observacao
            FROM read_parquet(?)
        )
        GROUP BY contrato_id, data_observacao
        HAVING COUNT(*) > 1
        """,
        paths,
    ).fetchall()

    assert len(duplicates) == 0


def test_future_target_windows_do_not_overlap(con):
    train = OUTPUT / "train.parquet"
    validation = OUTPUT / "validation.parquet"
    test = OUTPUT / "test.parquet"

    train_end = con.execute(
        """
        SELECT MAX(data_observacao)
        FROM read_parquet(?)
        """,
        [str(train)],
    ).fetchone()[0]

    validation_start, validation_end = con.execute(
        """
        SELECT
            MIN(data_observacao),
            MAX(data_observacao)
        FROM read_parquet(?)
        """,
        [str(validation)],
    ).fetchone()

    test_start = con.execute(
        """
        SELECT MIN(data_observacao)
        FROM read_parquet(?)
        """,
        [str(test)],
    ).fetchone()[0]

    assert (validation_start - train_end).days > 7
    assert (test_start - validation_end).days > 7
