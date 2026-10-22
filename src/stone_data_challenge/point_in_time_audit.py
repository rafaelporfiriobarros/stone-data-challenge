
import csv
import json

import duckdb

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR


DATASET = (
    DATA_DIR
    / "analytics"
    / "contrato_observacao_7d_v2.parquet"
)

PORTFOLIO = DATA_DIR / "gold" / "fact_contrato_diario.parquet"

COMMUNICATIONS = DATA_DIR / "gold" / "fact_comunicacoes.parquet"

OUTPUT = REPORTS_DIR / "point_in_time_audit"

START_DATE = "2022-01-10"
END_DATE = "2022-04-11"

# A auditoria considera eventos anteriores à data
# de observação, excluindo o próprio dia.
WINDOW_7 = 7
WINDOW_30 = 30


def sql_path(path):
    """Escapa caminhos controlados pelo projeto."""
    return path.as_posix().replace("'", "''")


def export_csv(con, query, path):
    result = con.execute(query)
    columns = [item[0] for item in result.description]
    rows = result.fetchall()

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)

    return len(rows)


def main():
    for path in (DATASET, PORTFOLIO, COMMUNICATIONS):
        if not path.exists():
            raise FileNotFoundError(path)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    dataset_path = sql_path(DATASET)
    portfolio_path = sql_path(PORTFOLIO)
    communications_path = sql_path(COMMUNICATIONS)

    con = duckdb.connect()

    try:
        # 1. Observacoes de validacao e teste.
        con.execute(
            f"""
            CREATE TEMP TABLE observations AS
            SELECT
                contrato_id,
                CAST(data_observacao AS DATE)
                    AS data_observacao,
                prazo,
                CAST(vlr_desembolsado AS DOUBLE)
                    AS vlr_desembolsado,
                CAST(perc_retencao AS DOUBLE)
                    AS perc_retencao,
                campanhas_7d,
                campanhas_30d,
                dias_com_acionamento_30d
            FROM read_parquet('{dataset_path}')
            WHERE CAST(data_observacao AS DATE)
                  BETWEEN DATE '{START_DATE}'
                      AND DATE '{END_DATE}'
            """
        )

        # 2. Snapshots historicos correspondentes.
        con.execute(
            f"""
            CREATE TEMP TABLE portfolio_asof AS
            SELECT
                o.contrato_id,
                o.data_observacao,
                p.prazo AS prazo_gold,
                CAST(p.vlr_desembolsado AS DOUBLE)
                    AS desembolso_gold,
                CAST(p.perc_retencao AS DOUBLE)
                    AS retencao_gold
            FROM observations o
            LEFT JOIN read_parquet('{portfolio_path}') p
                ON o.contrato_id = p.contrato_id
               AND o.data_observacao =
                   CAST(p.dt_ref_portfolio AS DATE)
            """
        )

        # 3. Eventos de campanhas anteriores
        # ao momento da observacao.
        #
        # A deduplicacao usa:
        # contrato_id, data_acao, acao.
        #
        # Isso evita contar EMAIL e HSM da mesma
        # campanha como campanhas independentes.
        con.execute(
            f"""
            CREATE TEMP TABLE campaigns AS
            SELECT DISTINCT
                contrato_id,
                CAST(data_acao AS DATE) AS data_acao,
                acao
            FROM read_parquet('{communications_path}')
            WHERE data_acao IS NOT NULL
            """
        )

        # 4. Reconstruir as janelas historicas.
        con.execute(
            """
            CREATE TEMP TABLE campaign_asof AS
            SELECT
                o.contrato_id,
                o.data_observacao,

                COUNT(c.data_acao) FILTER (
                    WHERE c.data_acao >=
                        o.data_observacao - INTERVAL 7 DAY
                ) AS campanhas_7d_gold,

                COUNT(c.data_acao)
                    AS campanhas_30d_gold,

                COUNT(DISTINCT c.data_acao)
                    AS dias_acionamento_30d_gold

            FROM observations o

            LEFT JOIN campaigns c
                ON o.contrato_id = c.contrato_id
               AND c.data_acao < o.data_observacao
               AND c.data_acao >=
                   o.data_observacao - INTERVAL 30 DAY

            GROUP BY
                o.contrato_id,
                o.data_observacao
            """
        )

        # 5. Comparar dataset e reconstrucoes.
        con.execute(
            """
            CREATE TEMP TABLE feature_audit AS
            SELECT
                o.*,

                p.prazo_gold,
                p.desembolso_gold,
                p.retencao_gold,

                c.campanhas_7d_gold,
                c.campanhas_30d_gold,
                c.dias_acionamento_30d_gold,

                CASE
                    WHEN p.contrato_id IS NULL THEN 1
                    ELSE 0
                END AS missing_portfolio,

                CASE
                    WHEN o.prazo IS DISTINCT FROM
                         p.prazo_gold
                    THEN 1 ELSE 0
                END AS mismatch_prazo,

                CASE
                    WHEN o.vlr_desembolsado IS DISTINCT FROM
                         p.desembolso_gold
                    THEN 1 ELSE 0
                END AS mismatch_desembolso,

                CASE
                    WHEN o.perc_retencao IS DISTINCT FROM
                         p.retencao_gold
                    THEN 1 ELSE 0
                END AS mismatch_retencao,

                CASE
                    WHEN o.campanhas_7d IS DISTINCT FROM
                         c.campanhas_7d_gold
                    THEN 1 ELSE 0
                END AS mismatch_campanhas_7d,

                CASE
                    WHEN o.campanhas_30d IS DISTINCT FROM
                         c.campanhas_30d_gold
                    THEN 1 ELSE 0
                END AS mismatch_campanhas_30d,

                CASE
                    WHEN o.dias_com_acionamento_30d
                         IS DISTINCT FROM
                         c.dias_acionamento_30d_gold
                    THEN 1 ELSE 0
                END AS mismatch_dias_acionamento

            FROM observations o

            LEFT JOIN portfolio_asof p
                ON o.contrato_id = p.contrato_id
               AND o.data_observacao =
                   p.data_observacao

            LEFT JOIN campaign_asof c
                ON o.contrato_id = c.contrato_id
               AND o.data_observacao =
                   c.data_observacao
            """
        )

        # 6. Resumo de divergencias.
        result = con.execute(
            """
            SELECT
                COUNT(*) AS observacoes,
                COUNT(DISTINCT (
                    contrato_id,
                    data_observacao
                )) AS chaves_unicas,

                SUM(missing_portfolio)
                    AS missing_portfolio,

                SUM(mismatch_prazo)
                    AS mismatch_prazo,

                SUM(mismatch_desembolso)
                    AS mismatch_desembolso,

                SUM(mismatch_retencao)
                    AS mismatch_retencao,

                SUM(mismatch_campanhas_7d)
                    AS mismatch_campanhas_7d,

                SUM(mismatch_campanhas_30d)
                    AS mismatch_campanhas_30d,

                SUM(mismatch_dias_acionamento)
                    AS mismatch_dias_acionamento

            FROM feature_audit
            """
        )

        columns = [item[0] for item in result.description]
        values = result.fetchone()
        metrics = dict(zip(columns, values))

        # 7. Exportar divergencias para inspeção.
        mismatch_columns = [
            "mismatch_prazo",
            "mismatch_desembolso",
            "mismatch_retencao",
            "mismatch_campanhas_7d",
            "mismatch_campanhas_30d",
            "mismatch_dias_acionamento",
        ]

        mismatch_filter = " OR ".join(
            f"{column} = 1"
            for column in mismatch_columns
        )

        exported = export_csv(
            con,
            f"""
            SELECT *
            FROM feature_audit
            WHERE missing_portfolio = 1
               OR {mismatch_filter}
            ORDER BY
                data_observacao,
                contrato_id
            LIMIT 1000
            """,
            OUTPUT / "feature_mismatches.csv",
        )

        # 8. Checagem das fronteiras temporais.
        temporal_boundaries = {
            "train_end": "2021-12-27",
            "validation_start": "2022-01-10",
            "validation_end": "2022-02-28",
            "test_start": "2022-03-14",
            "target_horizon_days": 7,
            "embargo_days": 14,
        }

        report = {
            "periodo": {
                "inicio": START_DATE,
                "fim": END_DATE,
            },
            "features": metrics,
            "divergencias_exportadas": exported,
            "fronteiras_temporais": temporal_boundaries,
            "criterio_temporal": (
                "Campanhas com data_acao anterior "
                "a data_observacao."
            ),
            "limitacoes": [
                "A comparacao valida consistencia "
                "historica, nao disponibilidade "
                "operacional em tempo real.",
                "Datas de eventos podem diferir "
                "de datas de ingestao.",
                "A semantica financeira do target "
                "ainda requer validacao externa.",
            ],
        }

        report_path = OUTPUT / "point_in_time_report.json"

        report_path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        print("\nSTONE | POINT-IN-TIME AUDIT")
        print("=" * 70)

        for key, value in metrics.items():
            print(f"{key}: {value}")

        print(
            "\nDivergencias exportadas:",
            exported,
        )

        print("[OK] Auditoria concluida")

    finally:
        con.close()


if __name__ == "__main__":
    main()
