
import duckdb

from stone_data_challenge.config import DATA_DIR


def main():
    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        sources = {
            "contratos": DATA_DIR / "silver" / "portfolio_geral.parquet",
            "comunicacoes": DATA_DIR / "silver" / "portfolio_comunicados.parquet",
            "clientes": DATA_DIR / "silver" / "portfolio_clientes.parquet",
        }

        for name, path in sources.items():
            if not path.exists():
                raise FileNotFoundError(path)

            safe_path = path.resolve().as_posix().replace("'", "''")
            con.execute(
                f"""
                CREATE TEMP VIEW {name} AS
                SELECT *
                FROM read_parquet('{safe_path}')
                """
            )

        def show(title, query):
            print(f"\n{title}")
            print("-" * 65)
            result = con.execute(query)
            columns = [c[0] for c in result.description]
            print(" | ".join(columns))
            for row in result.fetchall():
                print(" | ".join(str(v) for v in row))

        show(
            "1. COMUNICACOES: COMBINACOES DE CANAL E STATUS",
            """
            SELECT
                tipo_acao,
                status,
                COUNT(*) AS registros,
                COUNT(DISTINCT contrato_id) AS contratos
            FROM comunicacoes
            GROUP BY tipo_acao, status
            ORDER BY registros DESC
            """,
        )

        show(
            "2. COMUNICACOES: DUPLICATAS EXATAS",
            """
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT (
                    contrato_id,
                    dt_ref_portfolio,
                    data_acao,
                    tipo_acao,
                    acao,
                    status
                )) AS linhas_distintas
            FROM comunicacoes
            """,
        )

        show(
            "3. COMUNICACOES: MULTIPLICIDADE POR ACAO",
            """
            WITH grupos AS (
                SELECT
                    contrato_id,
                    data_acao,
                    tipo_acao,
                    acao,
                    COUNT(*) AS registros,
                    COUNT(DISTINCT status) AS status_distintos
                FROM comunicacoes
                GROUP BY
                    contrato_id,
                    data_acao,
                    tipo_acao,
                    acao
            )
            SELECT
                registros,
                status_distintos,
                COUNT(*) AS grupos
            FROM grupos
            GROUP BY registros, status_distintos
            ORDER BY registros, status_distintos
            """,
        )

        show(
            "4. PAGAMENTOS: VALORES POR STATUS",
            """
            SELECT
                status_contrato,
                COUNT(*) AS snapshots,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado > 0
                ) AS pagamento_positivo,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado = 0
                ) AS pagamento_zero,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado < 0
                ) AS pagamento_negativo
            FROM contratos
            GROUP BY status_contrato
            ORDER BY snapshots DESC
            """,
        )

        show(
            "5. PAGAMENTOS: MOVIMENTOS ENTRE DIAS",
            """
            WITH historico AS (
                SELECT
                    contrato_id,
                    dt_ref_portfolio,
                    vlr_pgto_realizado,
                    LAG(vlr_pgto_realizado) OVER (
                        PARTITION BY contrato_id
                        ORDER BY dt_ref_portfolio
                    ) AS valor_anterior,
                    LAG(dt_ref_portfolio) OVER (
                        PARTITION BY contrato_id
                        ORDER BY dt_ref_portfolio
                    ) AS data_anterior
                FROM contratos
            )
            SELECT
                CASE
                    WHEN valor_anterior IS NULL THEN 'PRIMEIRO'
                    WHEN vlr_pgto_realizado > valor_anterior
                        THEN 'AUMENTOU'
                    WHEN vlr_pgto_realizado < valor_anterior
                        THEN 'DIMINUIU'
                    ELSE 'IGUAL'
                END AS movimento,
                COUNT(*) AS snapshots,
                COUNT(*) FILTER (
                    WHERE data_anterior IS NOT NULL
                      AND date_diff(
                          'day',
                          data_anterior,
                          dt_ref_portfolio
                      ) = 1
                ) AS intervalo_um_dia
            FROM historico
            GROUP BY 1
            ORDER BY snapshots DESC
            """,
        )

        show(
            "6. CLIENTES: CONFLITOS POR ATRIBUTO",
            """
            WITH conflitos AS (
                SELECT
                    nr_documento,
                    COUNT(DISTINCT tipo_empresa) AS tipos,
                    COUNT(DISTINCT cidade) AS cidades,
                    COUNT(DISTINCT estado) AS estados,
                    COUNT(DISTINCT subsegmento) AS subsegmentos,
                    COUNT(DISTINCT segmento) AS segmentos
                FROM clientes
                GROUP BY nr_documento
            )
            SELECT
                COUNT(*) FILTER (WHERE tipos > 1)
                    AS conflitos_tipo_empresa,
                COUNT(*) FILTER (WHERE cidades > 1)
                    AS conflitos_cidade,
                COUNT(*) FILTER (WHERE estados > 1)
                    AS conflitos_estado,
                COUNT(*) FILTER (WHERE subsegmentos > 1)
                    AS conflitos_subsegmento,
                COUNT(*) FILTER (WHERE segmentos > 1)
                    AS conflitos_segmento
            FROM conflitos
            """,
        )

        print("\n[OK] Diagnostico de granularidade concluido")

    finally:
        con.close()


if __name__ == "__main__":
    main()
