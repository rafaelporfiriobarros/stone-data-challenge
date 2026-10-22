
import duckdb

from stone_data_challenge.config import DATA_DIR


GOLD = DATA_DIR / "gold"


def register_views(con):
    sources = {
        "contratos": "fact_contrato_diario",
        "comunicacoes": "fact_comunicacoes",
    }

    for alias, filename in sources.items():
        path = GOLD / f"{filename}.parquet"

        if not path.exists():
            raise FileNotFoundError(path)

        safe_path = path.resolve().as_posix().replace(
            "'", "''"
        )

        con.execute(
            f"""
            CREATE TEMP VIEW {alias} AS
            SELECT *
            FROM read_parquet('{safe_path}')
            """
        )


def show(con, title, query):
    print(f"\n{title}")
    print("-" * 65)

    result = con.execute(query)
    columns = [column[0] for column in result.description]

    print(" | ".join(columns))

    for row in result.fetchall():
        print(" | ".join(str(value) for value in row))


def main():
    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        register_views(con)

        print("\nSTONE | ANALYTICS DIAGNOSTICS")
        print("=" * 65)

        show(
            con,
            "1. PAGAMENTOS POR MES",
            """
            SELECT
                DATE_TRUNC(
                    'month',
                    dt_ref_portfolio
                )::DATE AS mes,
                COUNT(*) AS snapshots,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado > 0
                ) AS snapshots_com_pagamento,
                SUM(
                    vlr_pgto_realizado
                ) AS soma_valores_reportados
            FROM contratos
            GROUP BY 1
            ORDER BY 1
            """,
        )

        show(
            con,
            "2. COMUNICACOES POR MES",
            """
            SELECT
                DATE_TRUNC(
                    'month',
                    data_acao
                )::DATE AS mes,
                COUNT(*) AS registros,
                COUNT(DISTINCT contrato_id)
                    AS contratos_acionados
            FROM comunicacoes
            GROUP BY 1
            ORDER BY 1
            """,
        )

        show(
            con,
            "3. COMUNICACOES COM SNAPSHOT NA MESMA DATA",
            """
            SELECT
                COUNT(*) AS comunicacoes,
                COUNT(*) FILTER (
                    WHERE p.contrato_id IS NOT NULL
                ) AS com_snapshot_mesmo_dia,
                COUNT(*) FILTER (
                    WHERE p.contrato_id IS NULL
                ) AS sem_snapshot_mesmo_dia
            FROM comunicacoes c
            LEFT JOIN contratos p
                ON c.contrato_id = p.contrato_id
               AND c.data_acao = p.dt_ref_portfolio
            """,
        )

        show(
            con,
            "4. PAGAMENTO REPORTADO NO DIA DA COMUNICACAO",
            """
            SELECT
                c.tipo_acao,
                c.status,
                COUNT(*) AS registros_com_snapshot,
                COUNT(*) FILTER (
                    WHERE p.vlr_pgto_realizado > 0
                ) AS registros_com_pagamento_positivo
            FROM comunicacoes c
            INNER JOIN contratos p
                ON c.contrato_id = p.contrato_id
               AND c.data_acao = p.dt_ref_portfolio
            GROUP BY 1, 2
            ORDER BY 1, 2
            """,
        )

        show(
            con,
            "5. DISTRIBUICAO DE COMUNICACOES POR CONTRATO",
            """
            WITH volume AS (
                SELECT
                    contrato_id,
                    COUNT(*) AS comunicacoes
                FROM comunicacoes
                GROUP BY contrato_id
            )
            SELECT
                MIN(comunicacoes) AS minimo,
                MAX(comunicacoes) AS maximo,
                AVG(comunicacoes) AS media,
                MEDIAN(comunicacoes) AS mediana,
                QUANTILE_CONT(
                    comunicacoes, 0.90
                ) AS percentil_90
            FROM volume
            """,
        )

        print("\n[OK] Diagnostico analitico concluido")

    finally:
        con.close()


if __name__ == "__main__":
    main()
