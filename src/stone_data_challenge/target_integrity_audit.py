
import json

import duckdb

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR


GOLD = DATA_DIR / "gold" / "fact_contrato_diario.parquet"

DATASET = (
    DATA_DIR
    / "analytics"
    / "contrato_observacao_7d_v2.parquet"
)

OUTPUT = REPORTS_DIR / "target_integrity"

START_DATE = "2022-01-10"
END_DATE = "2022-04-11"


def query_one(con, sql, params=None):
    return con.execute(sql, params or []).fetchone()


def main():
    for path in (GOLD, DATASET):
        if not path.exists():
            raise FileNotFoundError(path)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    try:
        # Consultas SELECT parametrizadas são usadas
        # antes de registrar as tabelas no DuckDB.
       
        # Preparar os caminhos dos arquivos Parquet.
        # Os caminhos sao definidos internamente pelo projeto.
        gold_path = GOLD.as_posix().replace("'", "''")
        dataset_path = DATASET.as_posix().replace("'", "''")

        # Historico diario dos contratos.
        # Incluimos o dia anterior ao inicio do periodo
        # para permitir o calculo do primeiro incremento.
        con.execute(
            f"""
            CREATE TEMP TABLE snapshots AS
            SELECT
                contrato_id,
                CAST(dt_ref_portfolio AS DATE) AS dt,
                CAST(vlr_pgto_realizado AS DOUBLE)
                    AS pagamento
            FROM read_parquet('{gold_path}')
            WHERE CAST(dt_ref_portfolio AS DATE)
                  >= DATE '{START_DATE}' - INTERVAL 1 DAY
              AND CAST(dt_ref_portfolio AS DATE)
                  <= DATE '{END_DATE}' + INTERVAL 7 DAY
            """
        )

        # Observacoes usadas no dataset preditivo.
        con.execute(
            f"""
            CREATE TEMP TABLE observations AS
            SELECT
                contrato_id,
                CAST(data_observacao AS DATE)
                    AS data_observacao,
                CAST(target_pagamento_7d AS INTEGER)
                    AS target_atual
            FROM read_parquet('{dataset_path}')
            WHERE CAST(data_observacao AS DATE)
                  >= DATE '{START_DATE}'
              AND CAST(data_observacao AS DATE)
                  <= DATE '{END_DATE}'
            """
        )


        # Evolução diária dos valores registrados.
        con.execute(
            """
            CREATE TEMP TABLE payment_history AS
            SELECT
                contrato_id,
                dt,
                pagamento,
                LAG(pagamento) OVER (
                    PARTITION BY contrato_id
                    ORDER BY dt
                ) AS pagamento_anterior,
                LAG(dt) OVER (
                    PARTITION BY contrato_id
                    ORDER BY dt
                ) AS data_anterior
            FROM snapshots
            """
        )

        # Incrementos só são classificados quando
        # existe um snapshot no dia imediatamente
        # anterior.
        con.execute(
            """
            CREATE TEMP TABLE payment_changes AS
            SELECT
                *,
                CASE
                    WHEN data_anterior = dt - 1
                    THEN pagamento - pagamento_anterior
                    ELSE NULL
                END AS delta_pagamento
            FROM payment_history
            """
        )

        evolution = con.execute(
            """
            SELECT
                COUNT(*) AS snapshots,
                COUNT(DISTINCT contrato_id)
                    AS contratos,
                COUNT(*) FILTER (
                    WHERE pagamento > 0
                ) AS snapshots_positivos,
                COUNT(*) FILTER (
                    WHERE delta_pagamento = 0
                      AND pagamento > 0
                ) AS positivos_repetidos,
                COUNT(*) FILTER (
                    WHERE delta_pagamento > 0
                ) AS incrementos_positivos,
                COUNT(*) FILTER (
                    WHERE delta_pagamento < 0
                ) AS reducoes,
                COUNT(*) FILTER (
                    WHERE data_anterior IS NOT NULL
                      AND data_anterior <> dt - 1
                ) AS lacunas_entre_snapshots,
                COUNT(*) FILTER (
                    WHERE pagamento IS NULL
                ) AS pagamentos_nulos
            FROM payment_changes
            """
        ).fetchone()

        evolution_columns = [
            "snapshots",
            "contratos",
            "snapshots_positivos",
            "positivos_repetidos",
            "incrementos_positivos",
            "reducoes",
            "lacunas_entre_snapshots",
            "pagamentos_nulos",
        ]

        evolution_report = dict(
            zip(evolution_columns, evolution)
        )

        # Reconstituir targets no horizonte futuro.
        # Exige 7 snapshots diários distintos.
        con.execute(
            """
            CREATE TEMP TABLE target_comparison AS
            SELECT
                o.contrato_id,
                o.data_observacao,
                o.target_atual,

                COUNT(DISTINCT p.dt)
                    AS dias_futuros_disponiveis,

                MAX(
                    CASE WHEN p.pagamento > 0
                         THEN 1 ELSE 0 END
                ) AS target_positivo,

                MAX(
                    CASE WHEN p.delta_pagamento > 0
                         THEN 1 ELSE 0 END
                ) AS target_incremento

            FROM observations o
            LEFT JOIN payment_changes p
                ON o.contrato_id = p.contrato_id
               AND p.dt > o.data_observacao
               AND p.dt <= o.data_observacao
                           + INTERVAL 7 DAY

            GROUP BY
                o.contrato_id,
                o.data_observacao,
                o.target_atual
            """
        )

        comparison = con.execute(
            """
            SELECT
                COUNT(*) AS observacoes,
                COUNT(*) FILTER (
                    WHERE dias_futuros_disponiveis = 7
                ) AS janelas_completas,

                COUNT(*) FILTER (
                    WHERE dias_futuros_disponiveis < 7
                ) AS janelas_incompletas,

                COUNT(*) FILTER (
                    WHERE dias_futuros_disponiveis = 7
                      AND target_atual <> target_positivo
                ) AS divergencias_target_atual,

                COUNT(*) FILTER (
                    WHERE dias_futuros_disponiveis = 7
                      AND target_atual <> target_incremento
                ) AS divergencias_incremento,

                AVG(target_atual) FILTER (
                    WHERE dias_futuros_disponiveis = 7
                ) AS taxa_target_atual,

                AVG(target_incremento) FILTER (
                    WHERE dias_futuros_disponiveis = 7
                ) AS taxa_target_incremento

            FROM target_comparison
            """
        ).fetchone()

        comparison_columns = [
            "observacoes",
            "janelas_completas",
            "janelas_incompletas",
            "divergencias_target_atual",
            "divergencias_incremento",
            "taxa_target_atual",
            "taxa_target_incremento",
        ]

        comparison_report = dict(
            zip(comparison_columns, comparison)
        )

        # Salvar amostra de divergências para
        # investigação manual posterior.
        con.execute(
            f"""
            COPY (
                SELECT *
                FROM target_comparison
                WHERE dias_futuros_disponiveis = 7
                  AND target_atual <> target_incremento
                ORDER BY
                    data_observacao,
                    contrato_id
                LIMIT 1000
            )
            TO '{(OUTPUT / "target_disagreements.csv").as_posix()}'
            (HEADER, DELIMITER ',')
            """
        )

        report = {
            "periodo": {
                "inicio": START_DATE,
                "fim": END_DATE,
            },
            "evolucao_pagamentos": evolution_report,
            "comparacao_targets": comparison_report,
            "interpretacao": {
                "target_atual": (
                    "Existencia de valor positivo "
                    "em snapshots futuros."
                ),
                "target_incremento": (
                    "Existencia de incremento positivo "
                    "em relacao ao snapshot anterior."
                ),
                "limite": (
                    "Incrementos nao comprovam "
                    "pagamentos reais sem validacao "
                    "da semantica da fonte."
                ),
            },
        }

        path = OUTPUT / "target_integrity_report.json"

        path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        print("\nSTONE | TARGET INTEGRITY AUDIT")
        print("=" * 70)

        print("\nEVOLUCAO DOS PAGAMENTOS")
        for key, value in evolution_report.items():
            print(f"{key}: {value}")

        print("\nCOMPARACAO DOS TARGETS")
        for key, value in comparison_report.items():
            print(f"{key}: {value}")

        print(f"\nRelatorios: {OUTPUT}")
        print("[OK] Auditoria concluida")

    finally:
        con.close()


if __name__ == "__main__":
    main()
