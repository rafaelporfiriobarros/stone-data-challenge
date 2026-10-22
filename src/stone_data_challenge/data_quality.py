
import json
from datetime import datetime, timezone

import duckdb

from stone_data_challenge.config import (
    DATA_DIR,
    REPORTS_DIR,
)


SILVER_DIR = DATA_DIR / "silver"


def scalar(con, query):
    return con.execute(query).fetchone()[0]


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        # Views temporárias sobre os arquivos Silver.

        for name in [
            "portfolio_geral",
            "portfolio_tpv",
            "portfolio_comunicados",
            "portfolio_clientes",
        ]:
            path = SILVER_DIR / f"{name}.parquet"

            if not path.exists():
                raise FileNotFoundError(path)

            # DuckDB não aceita parâmetros preparados
            # em CREATE VIEW. Escapamos o caminho
            # antes de inseri-lo na expressão SQL.
            safe_path = path.resolve().as_posix().replace(
                "'", "''"
            )

            con.execute(
                f"""
                CREATE OR REPLACE TEMP VIEW "{name}" AS
                SELECT *
                FROM read_parquet('{safe_path}')
                """
            )

            print(f"[OK] View criada: {name}")


        report = {}

        print("\nSTONE | DATA QUALITY")
        print("=" * 65)

        # 1. Duplicidade de clientes.
        report["clientes"] = con.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT nr_documento)
                    AS documentos_distintos,
                COUNT(*) -
                    COUNT(DISTINCT nr_documento)
                    AS registros_excedentes
            FROM portfolio_clientes
        """).fetchone()

        # Identifica documentos com atributos
        # diferentes, não apenas linhas repetidas.
        report["clientes_conflitantes"] = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM (
                SELECT nr_documento
                FROM portfolio_clientes
                GROUP BY nr_documento
                HAVING COUNT(DISTINCT (
                    tipo_empresa, cidade, estado,
                    subsegmento, segmento
                )) > 1
            )
            """,
        )

        # 2. Criar conjuntos distintos para evitar
        # multiplicação de linhas nos relacionamentos.
        con.execute("""
            CREATE TEMP TABLE contratos_ids AS
            SELECT DISTINCT contrato_id
            FROM portfolio_geral
        """)

        con.execute("""
            CREATE TEMP TABLE documentos_contratos AS
            SELECT DISTINCT nr_documento
            FROM portfolio_geral
        """)

        con.execute("""
            CREATE TEMP TABLE documentos_clientes AS
            SELECT DISTINCT nr_documento
            FROM portfolio_clientes
        """)

        # 3. Comunicações sem contrato.
        report["comunicacoes_sem_contrato"] = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM portfolio_comunicados c
            ANTI JOIN contratos_ids p
                ON c.contrato_id = p.contrato_id
            """,
        )

        # 4. Documentos de contratos sem cadastro.
        report["documentos_sem_cliente"] = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM documentos_contratos p
            ANTI JOIN documentos_clientes c
                ON p.nr_documento = c.nr_documento
            """,
        )

        # 5. Datas inconsistentes.
        report["contratos_data_invalida"] = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM portfolio_geral
            WHERE dt_desembolso < dt_contrato
               OR dt_ref_portfolio < dt_contrato
            """,
        )

        # 6. Valores financeiros suspeitos.
        report["saldos_negativos"] = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM portfolio_geral
            WHERE vlr_saldo_devedor < 0
            """,
        )

        report["desembolsos_negativos"] = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM portfolio_geral
            WHERE vlr_desembolsado < 0
            """,
        )

        # 7. Quantidade de contratos únicos.
        report["contratos_distintos"] = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM contratos_ids
            """,
        )

        # 8. Cobertura temporal.
        report["periodo_contratos"] = con.execute(
            """
            SELECT
                MIN(dt_ref_portfolio),
                MAX(dt_ref_portfolio)
            FROM portfolio_geral
            """
        ).fetchone()

        report["periodo_comunicacoes"] = con.execute(
            """
            SELECT
                MIN(data_acao),
                MAX(data_acao)
            FROM portfolio_comunicados
            """
        ).fetchone()

        report["periodo_tpv"] = con.execute(
            """
            SELECT
                MIN(dt_transacao),
                MAX(dt_transacao)
            FROM portfolio_tpv
            """
        ).fetchone()

        for key, value in report.items():
            print(f"{key}: {value}")

        output = REPORTS_DIR / "data_quality_report.json"

        output.write_text(
            json.dumps(
                {
                    "executed_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "results": report,
                },
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        print("\n[OK] Auditoria concluída")
        print(f"Relatório: {output}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
