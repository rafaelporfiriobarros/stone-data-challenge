
import json
from datetime import datetime, timezone

import duckdb

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR


GOLD = DATA_DIR / "gold"
ANALYTICS = DATA_DIR / "analytics"


def sql_path(path):
    return path.resolve().as_posix().replace("'", "''")


def main():
    ANALYTICS.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    contracts_path = GOLD / "fact_contrato_diario.parquet"
    communications_path = GOLD / "fact_comunicacoes.parquet"

    for path in [contracts_path, communications_path]:
        if not path.exists():
            raise FileNotFoundError(path)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        con.execute(
            f"""
            CREATE TEMP VIEW contratos AS
            SELECT *
            FROM read_parquet('{sql_path(contracts_path)}')
            """
        )

        con.execute(
            f"""
            CREATE TEMP VIEW comunicacoes AS
            SELECT *
            FROM read_parquet('{sql_path(communications_path)}')
            """
        )

        output = ANALYTICS / "contrato_observacao_7d.parquet"

        query = """
        WITH futuro AS (
            SELECT
                contrato_id,
                nr_documento,
                dt_ref_portfolio AS data_observacao,
                status_contrato,
                safra,
                prazo,
                dsp,
                dspp,
                flag_transacao,
                vlr_desembolsado,
                vlr_saldo_devedor,
                vlr_pgto_realizado,
                perc_retencao,

                LEAD(dt_ref_portfolio, 7) OVER (
                    PARTITION BY contrato_id
                    ORDER BY dt_ref_portfolio
                ) AS data_setimo_snapshot,

                COUNT(*) FILTER (
                    WHERE vlr_pgto_realizado > 0
                ) OVER (
                    PARTITION BY contrato_id
                    ORDER BY dt_ref_portfolio
                    ROWS BETWEEN 1 FOLLOWING
                             AND 7 FOLLOWING
                ) AS dias_com_pagamento_futuro

            FROM contratos
        ),

        observacoes AS (
            SELECT
                *,
                CAST(
                    dias_com_pagamento_futuro > 0
                    AS INTEGER
                ) AS target_pagamento_7d
            FROM futuro
            WHERE status_contrato = 'Active'
              AND EXTRACT(
                  ISODOW FROM data_observacao
              ) = 1
              AND data_setimo_snapshot =
                  data_observacao + 7
        ),

        comunicacoes_diarias AS (
            SELECT
                contrato_id,
                data_acao,
                COUNT(*) AS registros_comunicacao,
                COUNT(*) FILTER (
                    WHERE tipo_acao = 'EMAIL'
                ) AS registros_email,
                COUNT(*) FILTER (
                    WHERE tipo_acao = 'HSM'
                ) AS registros_hsm
            FROM comunicacoes
            GROUP BY contrato_id, data_acao
        ),

        historico AS (
            SELECT
                o.contrato_id,
                o.data_observacao,

                COALESCE(
                    SUM(c.registros_comunicacao)
                    FILTER (
                        WHERE c.data_acao >=
                            o.data_observacao - 7
                    ),
                    0
                ) AS comunicacoes_7d,

                COALESCE(
                    SUM(c.registros_comunicacao),
                    0
                ) AS comunicacoes_30d,

                COALESCE(
                    SUM(c.registros_email),
                    0
                ) AS emails_30d,

                COALESCE(
                    SUM(c.registros_hsm),
                    0
                ) AS hsm_30d,

                COUNT(DISTINCT c.data_acao)
                    AS dias_com_acionamento_30d

            FROM observacoes o

            LEFT JOIN comunicacoes_diarias c
                ON o.contrato_id = c.contrato_id
               AND c.data_acao >=
                   o.data_observacao - 30
               AND c.data_acao <
                   o.data_observacao

            GROUP BY
                o.contrato_id,
                o.data_observacao
        )

        SELECT
            o.contrato_id,
            o.nr_documento,
            o.data_observacao,
            o.status_contrato,
            o.safra,
            o.prazo,
            o.dsp,
            o.dspp,
            o.flag_transacao,
            o.vlr_desembolsado,
            o.vlr_saldo_devedor,
            o.vlr_pgto_realizado,
            o.perc_retencao,

            h.comunicacoes_7d,
            h.comunicacoes_30d,
            h.emails_30d,
            h.hsm_30d,
            h.dias_com_acionamento_30d,

            o.target_pagamento_7d

        FROM observacoes o
        INNER JOIN historico h
            ON o.contrato_id = h.contrato_id
           AND o.data_observacao = h.data_observacao
        """

        con.execute(
            f"""
            COPY ({query})
            TO '{sql_path(output)}'
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )

        summary = con.execute(
            """
            SELECT
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,
                MIN(data_observacao) AS primeira_data,
                MAX(data_observacao) AS ultima_data,
                SUM(target_pagamento_7d) AS positivos,
                AVG(target_pagamento_7d) AS taxa_positivos,
                AVG(comunicacoes_30d) AS media_comunicacoes_30d
            FROM read_parquet(?)
            """,
            [str(output)],
        ).fetchone()

        labels = [
            "observacoes",
            "contratos",
            "primeira_data",
            "ultima_data",
            "positivos",
            "taxa_positivos",
            "media_comunicacoes_30d",
        ]

        report = dict(zip(labels, summary))

        print("\nSTONE | ML DATASET")
        print("=" * 65)

        for key, value in report.items():
            print(f"{key}: {value}")

        report_path = REPORTS_DIR / "ml_dataset_report.json"

        report_path.write_text(
            json.dumps(
                {
                    "executed_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "dataset": str(output),
                    "summary": report,
                },
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        print("\n[OK] Base analitica criada")
        print(f"Arquivo: {output}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
