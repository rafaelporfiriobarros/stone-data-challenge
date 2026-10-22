
import duckdb

from stone_data_challenge.config import DATA_DIR


GOLD = DATA_DIR / "gold"


def register_view(con, alias, filename):
    path = GOLD / f"{filename}.parquet"

    if not path.exists():
        raise FileNotFoundError(path)

    safe_path = path.resolve().as_posix().replace("'", "''")

    con.execute(
        f"""
        CREATE TEMP VIEW {alias} AS
        SELECT *
        FROM read_parquet('{safe_path}')
        """
    )


def show(con, title, query):
    result = con.execute(query)

    print(f"\n{title}")
    print("-" * 70)
    print(" | ".join(col[0] for col in result.description))

    for row in result.fetchall():
        print(" | ".join(str(value) for value in row))


def main():
    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        register_view(
            con, "comunicacoes", "fact_comunicacoes"
        )
        register_view(
            con, "contratos", "fact_contrato_diario"
        )

        print("\nSTONE | CAMPAIGN DIAGNOSTICS")
        print("=" * 70)

        show(
            con,
            "1. REGISTROS POR CONTRATO, DATA E CAMPANHA",
            """
            WITH grupos AS (
                SELECT
                    contrato_id,
                    data_acao,
                    acao,
                    COUNT(*) AS registros,
                    COUNT(DISTINCT tipo_acao) AS canais,
                    COUNT(DISTINCT status) AS statuses
                FROM comunicacoes
                GROUP BY 1, 2, 3
            )
            SELECT
                registros,
                canais,
                COUNT(*) AS grupos
            FROM grupos
            GROUP BY 1, 2
            ORDER BY 1, 2
            """,
        )

        show(
            con,
            "2. DISTRIBUICAO DOS CANAIS POR CAMPANHA",
            """
            SELECT
                acao,
                tipo_acao,
                COUNT(*) AS registros,
                COUNT(DISTINCT contrato_id)
                    AS contratos
            FROM comunicacoes
            GROUP BY 1, 2
            ORDER BY 1, 2
            """,
        )

        show(
            con,
            "3. REGISTROS VERSUS CAMPANHAS DISTINTAS",
            """
            SELECT
                COUNT(*) AS registros,
                COUNT(DISTINCT (
                    contrato_id, data_acao, acao
                )) AS contrato_dia_campanha,
                COUNT(DISTINCT (
                    contrato_id, data_acao, acao,
                    tipo_acao
                )) AS contrato_dia_campanha_canal
            FROM comunicacoes
            """,
        )

        show(
            con,
            "4. DIFERENCA ENTRE DATA DA ACAO E REFERENCIA",
            """
            SELECT
                DATE_DIFF(
                    'day',
                    data_acao,
                    dt_ref_portfolio
                ) AS diferenca_dias,
                COUNT(*) AS registros
            FROM comunicacoes
            GROUP BY 1
            ORDER BY registros DESC
            LIMIT 15
            """,
        )

        show(
            con,
            "5. DISTRIBUICAO DOS STATUS POR CAMPANHA",
            """
            SELECT
                acao,
                status,
                COUNT(*) AS registros
            FROM comunicacoes
            GROUP BY 1, 2
            ORDER BY 1, 2
            """,
        )

        print("\n[OK] Auditoria de campanhas concluida")

    finally:
        con.close()


if __name__ == "__main__":
    main()
