
import duckdb

from stone_data_challenge.config import DATA_DIR


def main():
    path = DATA_DIR / "gold" / "fact_contrato_diario.parquet"

    if not path.exists():
        raise FileNotFoundError(path)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        safe_path = path.resolve().as_posix().replace("'", "''")

        con.execute(
            f"""
            CREATE TEMP VIEW contratos AS
            SELECT *
            FROM read_parquet('{safe_path}')
            """
        )

        print("\nSTONE | TARGET DIAGNOSTICS")
        print("=" * 65)

        # Uma janela de 7 dias exige 7 snapshots
        # futuros consecutivos do mesmo contrato.
        #
        # Como a chave contrato-data é única,
        # podemos usar uma janela ROWS e conferir
        # a data do sétimo registro futuro.

        result = con.execute("""
            WITH janelas AS (
                SELECT
                    contrato_id,
                    dt_ref_portfolio,
                    status_contrato,
                    LEAD(dt_ref_portfolio, 7) OVER w
                        AS data_setimo_snapshot,

                    COUNT(*) FILTER (
                        WHERE vlr_pgto_realizado > 0
                    ) OVER (
                        PARTITION BY contrato_id
                        ORDER BY dt_ref_portfolio
                        ROWS BETWEEN 1 FOLLOWING
                                 AND 7 FOLLOWING
                    ) AS dias_pagamento_positivo,

                    SUM(
                        CASE
                            WHEN vlr_pgto_realizado > 0
                            THEN vlr_pgto_realizado
                            ELSE 0
                        END
                    ) OVER (
                        PARTITION BY contrato_id
                        ORDER BY dt_ref_portfolio
                        ROWS BETWEEN 1 FOLLOWING
                                 AND 7 FOLLOWING
                    ) AS valor_positivo_reportado_7d

                FROM contratos

                WINDOW w AS (
                    PARTITION BY contrato_id
                    ORDER BY dt_ref_portfolio
                )
            ),
            avaliacao AS (
                SELECT
                    *,
                    data_setimo_snapshot =
                        dt_ref_portfolio + 7
                        AS janela_completa
                FROM janelas
            )
            SELECT
                COUNT(*) AS observacoes,
                COUNT(*) FILTER (
                    WHERE janela_completa
                ) AS janelas_completas,
                COUNT(*) FILTER (
                    WHERE NOT COALESCE(
                        janela_completa, FALSE
                    )
                ) AS janelas_incompletas,
                COUNT(*) FILTER (
                    WHERE janela_completa
                      AND dias_pagamento_positivo > 0
                ) AS janelas_com_pagamento,
                COUNT(*) FILTER (
                    WHERE janela_completa
                      AND dias_pagamento_positivo = 0
                ) AS janelas_sem_pagamento,
                COUNT(DISTINCT contrato_id) FILTER (
                    WHERE janela_completa
                ) AS contratos_com_janela,
                SUM(valor_positivo_reportado_7d) FILTER (
                    WHERE janela_completa
                ) AS soma_valores_positivos_janelas
            FROM avaliacao
        """).fetchone()

        labels = [
            "observacoes",
            "janelas_completas",
            "janelas_incompletas",
            "janelas_com_pagamento",
            "janelas_sem_pagamento",
            "contratos_com_janela",
            "soma_valores_positivos_janelas",
        ]

        for label, value in zip(labels, result):
            print(f"{label}: {value}")

        if result[1]:
            taxa = 100 * result[3] / result[1]
            print(
                "taxa_janelas_com_pagamento: "
                f"{taxa:.2f}%"
            )

        print("\n[OK] Diagnostico de target concluido")

    finally:
        con.close()


if __name__ == "__main__":
    main()
