
import csv
import json
from datetime import datetime, timezone

import duckdb

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR


SOURCE = (
    DATA_DIR
    / "analytics"
    / "contrato_observacao_7d_v2.parquet"
)

OUTPUT = DATA_DIR / "ml"
REPORT = REPORTS_DIR / "temporal_split_report.json"


SPLITS = {
    "train": ("2020-01-06", "2021-12-27"),
    "validation": ("2022-01-10", "2022-02-28"),
    "test": ("2022-03-14", "2022-04-11"),
}


def safe_path(path):
    return path.resolve().as_posix().replace("'", "''")


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    report = {}

    try:
        con.execute(
            f"""
            CREATE TEMP VIEW base AS
            SELECT *
            FROM read_parquet('{safe_path(SOURCE)}')
            """
        )

        print("\nSTONE | TEMPORAL SPLIT")
        print("=" * 70)

        for name, (start, end) in SPLITS.items():
            destination = OUTPUT / f"{name}.parquet"

            con.execute(
                f"""
                COPY (
                    SELECT *
                    FROM base
                    WHERE data_observacao
                        BETWEEN DATE '{start}'
                            AND DATE '{end}'
                )
                TO '{safe_path(destination)}'
                (FORMAT PARQUET, COMPRESSION ZSTD)
                """
            )

            result = con.execute(
                """
                SELECT
                    COUNT(*) AS observacoes,
                    COUNT(DISTINCT contrato_id)
                        AS contratos,
                    MIN(data_observacao)
                        AS primeira_data,
                    MAX(data_observacao)
                        AS ultima_data,
                    SUM(target_pagamento_7d)
                        AS positivos,
                    ROUND(
                        100.0 * AVG(target_pagamento_7d),
                        2
                    ) AS taxa_positivos_pct,
                    ROUND(
                        AVG(CAST(campanhas_30d AS DOUBLE)),
                        3
                    ) AS media_campanhas_30d
                FROM read_parquet(?)
                """,
                [str(destination)],
            ).fetchone()

            fields = [
                "observacoes",
                "contratos",
                "primeira_data",
                "ultima_data",
                "positivos",
                "taxa_positivos_pct",
                "media_campanhas_30d",
            ]

            report[name] = dict(zip(fields, result))

            print(f"\n{name.upper()}")
            for key, value in report[name].items():
                print(f"{key}: {value}")

            if result[0] == 0:
                raise ValueError(
                    f"Conjunto vazio: {name}"
                )

        total_source = con.execute(
            "SELECT COUNT(*) FROM base"
        ).fetchone()[0]

        total_split = sum(
            item["observacoes"]
            for item in report.values()
        )

        report["excluded_observations"] = (
            total_source - total_split
        )

        report["generated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        REPORT.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        print(
            "\nObservacoes excluidas:",
            report["excluded_observations"],
        )
        print(f"Arquivos: {OUTPUT}")
        print("\n[OK] Divisao temporal concluida")

    finally:
        con.close()


if __name__ == "__main__":
    main()
