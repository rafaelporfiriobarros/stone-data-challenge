
import csv

import duckdb

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR


SOURCE = (
    DATA_DIR
    / "analytics"
    / "contrato_observacao_7d_v2.parquet"
)

OUTPUT = REPORTS_DIR / "campaign_eda_v2"


def save_report(con, title, query, filename):
    result = con.execute(query)

    columns = [
        column[0]
        for column in result.description
    ]

    rows = result.fetchall()

    print(f"\n{title}")
    print("-" * 75)
    print(" | ".join(columns))

    for row in rows:
        print(" | ".join(str(value) for value in row))

    destination = OUTPUT / filename

    with destination.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        safe_path = (
            SOURCE.resolve()
            .as_posix()
            .replace("'", "''")
        )

        con.execute(
            f"""
            CREATE TEMP VIEW base AS
            SELECT *
            FROM read_parquet('{safe_path}')
            """
        )

        con.execute(
            """
            CREATE TEMP VIEW analise AS
            SELECT
                *,
                CASE
                    WHEN campanhas_30d = 0 THEN '0'
                    WHEN campanhas_30d = 1 THEN '1'
                    WHEN campanhas_30d = 2 THEN '2'
                    WHEN campanhas_30d BETWEEN 3 AND 5
                        THEN '3-5'
                    WHEN campanhas_30d BETWEEN 6 AND 10
                        THEN '6-10'
                    ELSE '11+'
                END AS faixa_campanhas,

                CASE
                    WHEN campanhas_30d = 0 THEN 0
                    WHEN campanhas_30d = 1 THEN 1
                    WHEN campanhas_30d = 2 THEN 2
                    WHEN campanhas_30d <= 5 THEN 3
                    WHEN campanhas_30d <= 10 THEN 4
                    ELSE 5
                END AS ordem_faixa,

                DATE_TRUNC(
                    'month',
                    data_observacao
                )::DATE AS mes

            FROM base
            """
        )

        print("\nSTONE | CAMPAIGN EDA V2")
        print("=" * 75)

        save_report(
            con,
            "1. PAGAMENTO POR QUANTIDADE DE CAMPANHAS",
            """
            SELECT
                faixa_campanhas,
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,

                ROUND(
                    100.0 * AVG(target_pagamento_7d),
                    2
                ) AS taxa_pagamento_pct,

                ROUND(
                    AVG(
                        CAST(campanhas_30d AS DOUBLE)
                    ),
                    2
                ) AS media_campanhas,

                ROUND(
                    AVG(CAST(dsp AS DOUBLE)),
                    2
                ) AS dsp_medio,

                ROUND(
                    AVG(
                        CAST(
                            vlr_saldo_devedor AS DOUBLE
                        )
                    ),
                    2
                ) AS saldo_medio

            FROM analise

            GROUP BY
                faixa_campanhas,
                ordem_faixa

            ORDER BY ordem_faixa
            """,
            "payment_by_campaign_band.csv",
        )

        save_report(
            con,
            "2. CAMPANHAS E PAGAMENTO POR MES",
            """
            SELECT
                mes,
                faixa_campanhas,
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,

                ROUND(
                    100.0 * AVG(target_pagamento_7d),
                    2
                ) AS taxa_pagamento_pct

            FROM analise

            GROUP BY
                mes,
                faixa_campanhas,
                ordem_faixa

            ORDER BY
                mes,
                ordem_faixa
            """,
            "monthly_campaign_bands.csv",
        )

        save_report(
            con,
            "3. ASSOCIACAO POR ANO",
            """
            SELECT
                EXTRACT(
                    YEAR FROM data_observacao
                )::INTEGER AS ano,

                faixa_campanhas,
                COUNT(*) AS observacoes,

                ROUND(
                    100.0 * AVG(target_pagamento_7d),
                    2
                ) AS taxa_pagamento_pct

            FROM analise

            GROUP BY
                ano,
                faixa_campanhas,
                ordem_faixa

            ORDER BY
                ano,
                ordem_faixa
            """,
            "yearly_campaign_bands.csv",
        )

        total = con.execute(
            "SELECT COUNT(*) FROM analise"
        ).fetchone()[0]

        print(f"\nTotal de observacoes: {total:,}")
        print(f"Relatorios: {OUTPUT}")
        print("\n[OK] Analise V2 concluida")

    finally:
        con.close()


if __name__ == "__main__":
    main()
