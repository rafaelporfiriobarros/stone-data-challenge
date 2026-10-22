
import json
from datetime import datetime, timezone

import duckdb

from stone_data_challenge.config import (
    DATA_DIR,
    REPORTS_DIR,
)

SILVER = DATA_DIR / "silver"
GOLD = DATA_DIR / "gold"

SOURCES = {
    "contratos": "portfolio_geral",
    "clientes": "portfolio_clientes",
    "comunicacoes": "portfolio_comunicados",
    "tpv": "portfolio_tpv",
}

MODELS = {
    "dim_clientes": """
        SELECT
            nr_documento,
            COUNT(*) AS registros_origem,
            COUNT(DISTINCT (
                tipo_empresa, cidade, estado,
                subsegmento, segmento
            )) > 1 AS cadastro_conflitante,

            CASE
                WHEN COUNT(DISTINCT tipo_empresa) = 1
                THEN MIN(tipo_empresa)
                ELSE 'CONFLITANTE'
            END AS tipo_empresa,

            CASE
                WHEN COUNT(DISTINCT cidade) = 1
                THEN MIN(cidade)
                ELSE 'CONFLITANTE'
            END AS cidade,

            CASE
                WHEN COUNT(DISTINCT estado) = 1
                THEN MIN(estado)
                ELSE 'CONFLITANTE'
            END AS estado,

            CASE
                WHEN COUNT(DISTINCT subsegmento) = 1
                THEN MIN(subsegmento)
                ELSE 'CONFLITANTE'
            END AS subsegmento,

            CASE
                WHEN COUNT(DISTINCT segmento) = 1
                THEN MIN(segmento)
                ELSE 'CONFLITANTE'
            END AS segmento

        FROM clientes
        GROUP BY nr_documento
    """,

    "dim_contratos": """
        SELECT
            contrato_id,
            CASE
                WHEN COUNT(DISTINCT nr_documento) = 1
                THEN MIN(nr_documento)
                ELSE NULL
            END AS nr_documento,
            COUNT(DISTINCT nr_documento) > 1
                AS documento_conflitante,
            MIN(dt_ref_portfolio) AS primeira_observacao,
            MAX(dt_ref_portfolio) AS ultima_observacao,
            COUNT(*) AS total_snapshots
        FROM contratos
        GROUP BY contrato_id
    """,

    "fact_contrato_diario": """
        SELECT
            contrato_id,
            nr_documento,
            dt_ref_portfolio,
            safra,
            status_contrato,
            dt_contrato,
            dt_desembolso,
            dt_vencimento,
            dt_wo,
            prazo,
            vlr_desembolsado,
            vlr_tarifa,
            juros_mes,
            juros_diario,
            perc_retencao,
            vlr_pgto_realizado,
            vlr_pgto_esperado,
            vlr_saldo_devedor,
            vlr_saldo_devedor_esperado,
            dsp,
            dspp,
            flag_transacao
        FROM contratos
    """,

    "fact_comunicacoes": """
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY
                    contrato_id,
                    data_acao,
                    dt_ref_portfolio,
                    tipo_acao,
                    acao,
                    status
            ) AS comunicacao_sk,
            contrato_id,
            dt_ref_portfolio,
            data_acao,
            tipo_acao,
            acao,
            status
        FROM comunicacoes
    """,

    "fact_tpv_diario": """
        SELECT
            nr_documento,
            dt_transacao,
            qtd_transacoes,
            vlr_tpv
        FROM tpv
    """,
}


def create_views(con):
    for alias, source in SOURCES.items():
        path = SILVER / f"{source}.parquet"

        if not path.exists():
            raise FileNotFoundError(path)

        safe_path = (
            path.resolve().as_posix().replace("'", "''")
        )

        con.execute(
            f"""
            CREATE TEMP VIEW "{alias}" AS
            SELECT *
            FROM read_parquet('{safe_path}')
            """
        )


def main():
    GOLD.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    report = {}

    try:
        create_views(con)

        print("\nSTONE | GOLD BUILD")
        print("=" * 65)

        for name, query in MODELS.items():
            destination = GOLD / f"{name}.parquet"

            # Não interpolar entradas externas em SQL.
            safe_destination = (
                destination.resolve()
                .as_posix()
                .replace("'", "''")
            )

            con.execute(
                f"""
                COPY (
                    {query}
                )
                TO '{safe_destination}'
                (
                    FORMAT PARQUET,
                    COMPRESSION ZSTD
                )
                """
            )

            count = con.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(destination)],
            ).fetchone()[0]

            report[name] = count
            print(f"[GOLD] {name}: {count:,} registros")

        output = REPORTS_DIR / "gold_report.json"

        output.write_text(
            json.dumps(
                {
                    "executed_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "tables": report,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print("\n[OK] Gold construída")
        print(f"Relatório: {output}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
