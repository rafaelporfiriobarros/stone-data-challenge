import json

import duckdb

from stone_data_challenge.config import (
    BRONZE_DIR,
    DATASETS,
    REPORTS_DIR,
)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    report = {}

    try:
        for name in DATASETS:
            path = BRONZE_DIR / f"{name}.parquet"

            if not path.exists():
                raise FileNotFoundError(path)

            total = con.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(path)],
            ).fetchone()[0]

            schema = con.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)",
                [str(path)],
            ).fetchall()

            columns = [
                {
                    "name": row[0],
                    "type": row[1],
                }
                for row in schema
            ]

            report[name] = {
                "rows": total,
                "columns": columns,
            }

            print(f"\nDATASET: {name}")
            print(f"Registros: {total:,}")
            print(f"Colunas: {len(columns)}")

            for column in columns:
                print(
                    f"  {column['name']}: "
                    f"{column['type']}"
                )

        output = REPORTS_DIR / "data_profile.json"

        output.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print(f"\n[OK] Profiling salvo em {output}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
