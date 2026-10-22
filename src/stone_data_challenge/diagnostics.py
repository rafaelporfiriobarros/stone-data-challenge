
import json

import duckdb

from stone_data_challenge.config import (
    BRONZE_DIR,
    DATASETS,
    REPORTS_DIR,
)


def inspect_dataset(con, name):
    path = BRONZE_DIR / f"{name}.parquet"

    print(f"\n{'=' * 65}")
    print(f"DATASET: {name}")
    print("=" * 65)

    schema = con.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(path)],
    ).fetchall()

    columns = [row[0] for row in schema]

    print("\nCOLUNAS:")
    for column in columns:
        print(f"  {column}")

    # Consulta agregada para contar nulos e strings vazias.
    expressions = [
        f"""
        COUNT(*) FILTER (
            WHERE "{column.replace('"', '""')}" IS NULL
               OR TRIM("{column.replace('"', '""')}") = ''
        ) AS "{column.replace('"', '""')}"
        """
        for column in columns
    ]

    query = f"""
        SELECT COUNT(*) AS total, {", ".join(expressions)}
        FROM read_parquet(?)
    """

    result = con.execute(query, [str(path)])
    row = result.fetchone()
    names = [item[0] for item in result.description]

    nulls = dict(zip(names[1:], row[1:]))

    print(f"\nTOTAL DE REGISTROS: {row[0]:,}")
    print("\nNULOS / VAZIOS:")

    for column, count in nulls.items():
        percentage = 100 * count / row[0] if row[0] else 0
        print(
            f"  {column}: {count:,} ({percentage:.2f}%)"
        )

    return {
        "dataset": name,
        "rows": row[0],
        "columns": columns,
        "null_counts": nulls,
    }


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        results = []

        for name in DATASETS:
            results.append(inspect_dataset(con, name))

        output = REPORTS_DIR / "diagnostics.json"

        output.write_text(
            json.dumps(
                results,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print(f"\n[OK] Diagnóstico salvo em {output}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
