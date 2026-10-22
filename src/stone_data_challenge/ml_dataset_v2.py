
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

    source = ANALYTICS / "contrato_observacao_7d.parquet"
    communications = GOLD / "fact_comunicacoes.parquet"
    destination = ANALYTICS / "contrato_observacao_7d_v2.parquet"

    for path in (source, communications):
        if not path.exists():
            raise FileNotFoundError(path)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    try:
        con.execute(
            f"""
            CREATE TEMP VIEW base AS
            SELECT *
            FROM read_parquet('{sql_path(source)}')
            """
        )

        con.execute(
            f"""
            CREATE TEMP VIEW comunicacoes AS
            SELECT *
            FROM read_parquet('{sql_path(communications)}')
            """
        )

        # Uma campanha é identificada por:
        # contrato_id + data_acao + acao.
        #
        # Preservamos também a quantidade de
        # registros e a presença de cada canal.
        con.execute(
            """
            CREATE TEMP VIEW campanhas AS
            SELECT
                contrato_id,
                data_acao,
                acao,
                COUNT(*) AS registros_brutos,
                COUNT(DISTINCT tipo_acao)
                    AS canais_distintos,
                MAX(
                    CASE WHEN tipo_acao = 'EMAIL'
                    THEN 1 ELSE 0 END
                ) AS possui_email,
                MAX(
                    CASE WHEN tipo_acao = 'HSM'
                    THEN 1 ELSE 0 END
                ) AS possui_hsm
            FROM comunicacoes
            GROUP BY
                contrato_id,
                data_acao,
                acao
            """
        )

        query = """
        WITH historico AS (
            SELECT
                b.contrato_id,
                b.data_observacao,

                COUNT(c.acao) FILTER (
                    WHERE c.data_acao >=
                        b.data_observacao - 7
                ) AS campanhas_7d,

                COUNT(c.acao)
                    AS campanhas_30d,

                COALESCE(
                    SUM(c.canais_distintos), 0
                ) AS acionamentos_canal_30d,

                COALESCE(
                    SUM(c.registros_brutos), 0
                ) AS registros_comunicacao_30d,

                COALESCE(
                    SUM(c.possui_email), 0
                ) AS emails_30d,

                COALESCE(
                    SUM(c.possui_hsm), 0
                ) AS hsm_30d,

                COUNT(DISTINCT c.data_acao)
                    AS dias_com_acionamento_30d

            FROM base b

            LEFT JOIN campanhas c
                ON b.contrato_id = c.contrato_id
               AND c.data_acao >=
                   b.data_observacao - 30
               AND c.data_acao <
                   b.data_observacao

            GROUP BY
                b.contrato_id,
                b.data_observacao
        )

        SELECT
            b.* EXCLUDE (
                comunicacoes_7d,
                comunicacoes_30d,
                emails_30d,
                hsm_30d,
                dias_com_acionamento_30d
            ),
            h.campanhas_7d,
            h.campanhas_30d,
            h.acionamentos_canal_30d,
            h.registros_comunicacao_30d,
            h.emails_30d,
            h.hsm_30d,
            h.dias_com_acionamento_30d,
            b.comunicacoes_7d
                AS registros_comunicacao_7d_original,
            b.comunicacoes_30d
                AS registros_comunicacao_30d_original

        FROM base b
        INNER JOIN historico h
            ON b.contrato_id = h.contrato_id
           AND b.data_observacao = h.data_observacao
        """

        con.execute(
            f"""
            COPY ({query})
            TO '{sql_path(destination)}'
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )

        summary = con.execute(
            """
            SELECT
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id)
                    AS contratos,
                AVG(CAST(campanhas_30d AS DOUBLE))
                    AS media_campanhas_30d,
                AVG(
                    CAST(
                        registros_comunicacao_30d
                        AS DOUBLE
                    )
                ) AS media_registros_30d,
                COUNT(*) FILTER (
                    WHERE campanhas_30d = 1
                ) AS observacoes_uma_campanha,
                AVG(target_pagamento_7d)
                    AS taxa_pagamento
            FROM read_parquet(?)
            """,
            [str(destination)],
        ).fetchone()

        labels = [
            "observacoes",
            "contratos",
            "media_campanhas_30d",
            "media_registros_30d",
            "observacoes_uma_campanha",
            "taxa_pagamento",
        ]

        report = dict(zip(labels, summary))

        print("\nSTONE | ML DATASET V2")
        print("=" * 65)

        for key, value in report.items():
            print(f"{key}: {value}")

        report_path = REPORTS_DIR / "ml_dataset_v2_report.json"

        report_path.write_text(
            json.dumps(
                {
                    "executed_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "dataset": str(destination),
                    "summary": report,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        print("\n[OK] Base analitica V2 criada")

    finally:
        con.close()


if __name__ == "__main__":
    main()
