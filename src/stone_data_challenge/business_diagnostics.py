
import duckdb

from stone_data_challenge.config import DATA_DIR

SILVER = DATA_DIR / "silver"


def main():
    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        paths = {
            "contratos": SILVER / "portfolio_geral.parquet",
            "clientes": SILVER / "portfolio_clientes.parquet",
            "comunicacoes": SILVER / "portfolio_comunicados.parquet",
        }

        for name, path in paths.items():
            if not path.exists():
                raise FileNotFoundError(path)

            safe_path = (
                path.resolve().as_posix().replace("'", "''")
            )

            con.execute(
                f"""
                CREATE TEMP VIEW {name} AS
                SELECT *
                FROM read_parquet('{safe_path}')
                """
            )

        print("\nSTONE | BUSINESS DIAGNOSTICS")
        print("=" * 65)

        # 1. Duplicatas exatas de clientes
        result = con.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT (
                    nr_documento,
                    tipo_empresa,
                    cidade,
                    estado,
                    subsegmento,
                    segmento
                )) AS linhas_distintas
            FROM clientes
        """).fetchone()

        print("\nCLIENTES:")
        print("Total de registros:", result[0])
        print("Linhas distintas:", result[1])
        print("Duplicatas exatas:", result[0] - result[1])

        # 2. Saldos negativos por status
        print("\nSALDOS NEGATIVOS POR STATUS:")

        rows = con.execute("""
            SELECT
                status_contrato,
                COUNT(*) AS registros,
                COUNT(DISTINCT contrato_id)
                    AS contratos,
                MIN(vlr_saldo_devedor) AS menor_saldo,
                MAX(vlr_saldo_devedor) AS maior_saldo
            FROM contratos
            WHERE vlr_saldo_devedor < 0
            GROUP BY status_contrato
            ORDER BY registros DESC
        """).fetchall()

        for row in rows:
            print(row)

        # 3. Perfil dos pagamentos
        print("\nPAGAMENTOS REALIZADOS:")

        result = con.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado > 0
                ) AS positivos,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado = 0
                ) AS zerados,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado < 0
                ) AS negativos,
                MIN(vlr_pgto_realizado),
                MAX(vlr_pgto_realizado)
            FROM contratos
        """).fetchone()

        print(result)

        # 4. Verificar se pagamento realizado
        # é crescente ao longo dos snapshots.
        print("\nEVOLUÇÃO DOS PAGAMENTOS:")

        result = con.execute("""
            WITH historico AS (
                SELECT
                    contrato_id,
                    dt_ref_portfolio,
                    vlr_pgto_realizado,
                    LAG(vlr_pgto_realizado) OVER (
                        PARTITION BY contrato_id
                        ORDER BY dt_ref_portfolio
                    ) AS pagamento_anterior
                FROM contratos
            )
            SELECT
                COUNT(*) FILTER (
                    WHERE pagamento_anterior IS NOT NULL
                ) AS comparacoes,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado >
                          pagamento_anterior
                ) AS aumentos,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado =
                          pagamento_anterior
                ) AS iguais,
                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado <
                          pagamento_anterior
                ) AS reducoes
            FROM historico
        """).fetchone()

        print(result)

        # 5. Verificar acionamentos simultâneos
        print("\nCOMUNICAÇÕES POR CONTRATO E DATA:")

        result = con.execute("""
            WITH grupos AS (
                SELECT
                    contrato_id,
                    data_acao,
                    COUNT(*) AS quantidade
                FROM comunicacoes
                GROUP BY contrato_id, data_acao
            )
            SELECT
                COUNT(*) AS grupos,
                COUNT(*) FILTER (
                    WHERE quantidade > 1
                ) AS grupos_multiplos,
                MAX(quantidade) AS max_acoes_mesmo_dia
            FROM grupos
        """).fetchone()

        print(result)

        print("\n[OK] Diagnóstico de negócio concluído")

    finally:
        con.close()


if __name__ == "__main__":
    main()
