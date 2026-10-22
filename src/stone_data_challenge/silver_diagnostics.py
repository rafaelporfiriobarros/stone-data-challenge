
import duckdb

from stone_data_challenge.config import BRONZE_DIR
from stone_data_challenge.silver import SCHEMAS, quote


def main():
    source = BRONZE_DIR / "portfolio_geral.parquet"
    schema = SCHEMAS["portfolio_geral"]

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        print("\nSTONE | DIAGNÓSTICO SILVER")
        print("=" * 65)

        checks = []

        for column in schema["dates"]:
            col = quote(column)
            checks.append((
                column,
                f"""TRY_STRPTIME(
                    {col}, '%Y-%m-%d'
                ) IS NULL"""
            ))

        for column in schema["decimal"]:
            col = quote(column)
            checks.append((
                column,
                f"""TRY_CAST(
                    {col} AS DECIMAL(28,8)
                ) IS NULL"""
            ))

        for column in schema["integer"]:
            col = quote(column)
            checks.append((
                column,
                f"TRY_CAST({col} AS BIGINT) IS NULL"
            ))

        expressions = [
            f"""COUNT(*) FILTER (
                WHERE {condition}
            ) AS {quote(column)}"""
            for column, condition in checks
        ]

        result = con.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                {", ".join(expressions)}
            FROM read_parquet(?)
            """,
            [str(source)],
        )

        row = result.fetchone()
        names = [item[0] for item in result.description]
        total = row[0]

        print(f"Registros: {total:,}")
        print("\nFALHAS DE CONVERSÃO POR COLUNA:")

        for column, count in zip(names[1:], row[1:]):
            percentage = count / total * 100

            print(
                f"{column:<30}"
                f"{count:>12,} "
                f"({percentage:6.2f}%)"
            )

        print("\nEXEMPLOS DE VALORES ORIGINAIS:")

        for column in ["safra", "dt_wo"]:
            col = quote(column)

            values = con.execute(
                f"""
                SELECT {col}, COUNT(*) AS total
                FROM read_parquet(?)
                GROUP BY {col}
                ORDER BY total DESC
                LIMIT 10
                """,
                [str(source)],
            ).fetchall()

            print(f"\n{column}:")
            for value, count in values:
                print(f"  {value!r}: {count:,}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
