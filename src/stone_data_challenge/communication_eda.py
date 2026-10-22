
import csv
from pathlib import Path

import duckdb

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR


SOURCE = (
    DATA_DIR / "analytics" / "contrato_observacao_7d.parquet"
)

OUTPUT = REPORTS_DIR / "communication_eda"


def save_csv(path: Path, columns, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)


def run_query(con, title, query, filename):
    result = con.execute(query)

    columns = [col[0] for col in result.description]
    rows = result.fetchall()

    print(f"\n{title}")
    print("-" * 70)
    print(" | ".join(columns))

    for row in rows:
        print(" | ".join(str(value) for value in row))

    save_csv(OUTPUT / filename, columns, rows)


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        safe_path = SOURCE.resolve().as_posix().replace(
            "'", "''"
        )

        con.execute(
            f"""
            CREATE TEMP VIEW base AS
            SELECT *
            FROM read_parquet('{safe_path}')
            """
        )

        print("\nSTONE | COMMUNICATION EDA")
        print("=" * 70)

        run_query(
            con,
            "1. TAXA DE PAGAMENTO POR FAIXA DE COMUNICACOES",
            """
            WITH faixas AS (
                SELECT
                    *,
                    CASE
                        WHEN comunicacoes_30d = 0 THEN '0'
                        WHEN comunicacoes_30d = 1 THEN '1'
                        WHEN comunicacoes_30d = 2 THEN '2'
                        WHEN comunicacoes_30d BETWEEN 3 AND 5
                            THEN '3-5'
                        WHEN comunicacoes_30d BETWEEN 6 AND 10
                            THEN '6-10'
                        ELSE '11+'
                    END AS faixa,
                    CASE
                        WHEN comunicacoes_30d = 0 THEN 0
                        WHEN comunicacoes_30d = 1 THEN 1
                        WHEN comunicacoes_30d = 2 THEN 2
                        WHEN comunicacoes_30d <= 5 THEN 3
                        WHEN comunicacoes_30d <= 10 THEN 4
                        ELSE 5
                    END AS ordem
                FROM base
            )
            SELECT
                faixa,
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,
                ROUND(
                    100 * AVG(target_pagamento_7d), 2
                ) AS taxa_pagamento_pct,
                ROUND(
                    AVG(CAST(comunicacoes_30d AS DOUBLE)), 2
                ) AS media_comunicacoes
            FROM faixas
            GROUP BY faixa, ordem
            ORDER BY ordem
            """,
            "payment_by_communication_band.csv",
        )

        run_query(
            con,
            "2. EVOLUCAO MENSAL",
            """
            SELECT
                DATE_TRUNC(
                    'month', data_observacao
                )::DATE AS mes,
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,
                ROUND(
                    100 * AVG(target_pagamento_7d), 2
                ) AS taxa_pagamento_pct,
                ROUND(
                    AVG(CAST(comunicacoes_30d AS DOUBLE)), 2
                ) AS media_comunicacoes_30d
            FROM base
            GROUP BY 1
            ORDER BY 1
            """,
            "monthly_trends.csv",
        )

        run_query(
            con,
            "3. COM E SEM COMUNICACAO RECENTE",
            """
            SELECT
                CASE
                    WHEN comunicacoes_7d > 0
                        THEN 'COM_COMUNICACAO'
                    ELSE 'SEM_COMUNICACAO'
                END AS grupo,
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,
                ROUND(
                    100 * AVG(target_pagamento_7d), 2
                ) AS taxa_pagamento_pct,
                ROUND(
                    AVG(CAST(vlr_saldo_devedor AS DOUBLE)), 2
                ) AS saldo_medio,
                ROUND(
                    AVG(CAST(dsp AS DOUBLE)), 2
                ) AS dsp_medio
            FROM base
            GROUP BY 1
            ORDER BY 1
            """,
            "communication_comparison.csv",
        )

        print("\n[OK] Analise exploratoria concluida")
        print(f"Relatorios: {OUTPUT}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
