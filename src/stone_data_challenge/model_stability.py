
import csv

import duckdb

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR


PREDICTIONS = (
    REPORTS_DIR
    / "final_evaluation"
    / "predictions.parquet"
)

TEST = DATA_DIR / "ml" / "test.parquet"

OUTPUT = REPORTS_DIR / "model_stability"


def export(con, filename, query):
    result = con.execute(query)
    columns = [item[0] for item in result.description]
    rows = result.fetchall()

    path = OUTPUT / filename

    with path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"\n{filename}")
    for row in rows:
        print(row)

    return rows


def main():
    if not PREDICTIONS.exists():
        raise FileNotFoundError(PREDICTIONS)

    if not TEST.exists():
        raise FileNotFoundError(TEST)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    
    
    # Carregar as previsoes do modelo
    predictions_df = con.execute(
        """
        SELECT
            contrato_id,
            data_observacao,
            target_pagamento_7d,
            probability_calibrated
        FROM read_parquet(?)
        """,
        [str(PREDICTIONS)],
    ).fetchdf()

    # Carregar os atributos do conjunto de teste
    test_df = con.execute(
        """
        SELECT
            contrato_id,
            data_observacao,
            campanhas_30d,
            prazo
        FROM read_parquet(?)
        """,
        [str(TEST)],
    ).fetchdf()

    # Registrar as fontes na conexao DuckDB
    con.register(
        "predictions_source",
        predictions_df,
    )

    con.register(
        "test_source",
        test_df,
    )


    try:
        
        # Registrar os arquivos Parquet como views
        # usando consultas SELECT parametrizadas.
        con.execute(
            """
            CREATE TEMP VIEW analysis AS
            SELECT
                p.contrato_id,
                p.data_observacao,
                p.target_pagamento_7d AS target,
                p.probability_calibrated AS probability,
                t.campanhas_30d,
                t.prazo
            FROM predictions_source p
            INNER JOIN test_source t
                ON p.contrato_id = t.contrato_id
               AND p.data_observacao = t.data_observacao
            """
        )


        counts = con.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT (
                    contrato_id, data_observacao
                )) AS unique_keys
            FROM analysis
            """
        ).fetchone()

        if counts != (31570, 31570):
            raise ValueError(
                f"Reconciliacao invalida: {counts}"
            )

        summary = """
            COUNT(*) AS observacoes,
            COUNT(DISTINCT contrato_id) AS contratos,
            ROUND(100 * AVG(target), 2)
                AS pagamento_observado_pct,
            ROUND(100 * AVG(probability), 2)
                AS probabilidade_prevista_pct,
            ROUND(
                100 * (AVG(probability) - AVG(target)),
                2
            ) AS desvio_pct_pontos,
            ROUND(
                AVG(POWER(probability - target, 2)),
                4
            ) AS brier_score
        """

        export(
            con,
            "stability_by_week.csv",
            f"""
            SELECT
                data_observacao AS semana,
                {summary}
            FROM analysis
            GROUP BY data_observacao
            ORDER BY data_observacao
            """,
        )

        export(
            con,
            "stability_by_campaign.csv",
            f"""
            SELECT
                CASE
                    WHEN campanhas_30d = 0 THEN '0'
                    WHEN campanhas_30d = 1 THEN '1'
                    WHEN campanhas_30d = 2 THEN '2'
                    WHEN campanhas_30d <= 5 THEN '3-5'
                    ELSE '6+'
                END AS faixa_campanhas,
                {summary}
            FROM analysis
            GROUP BY faixa_campanhas
            ORDER BY faixa_campanhas
            """,
        )

        export(
            con,
            "stability_by_term.csv",
            f"""
            SELECT
                CASE
                    WHEN prazo IS NULL THEN 'DESCONHECIDO'
                    WHEN prazo <= 30 THEN 'ATE_30'
                    WHEN prazo <= 90 THEN '31_90'
                    WHEN prazo <= 180 THEN '91_180'
                    ELSE '181_MAIS'
                END AS faixa_prazo,
                {summary}
            FROM analysis
            GROUP BY faixa_prazo
            ORDER BY faixa_prazo
            """,
        )

        print("\n[OK] Auditoria concluida")

    finally:
        con.close()


if __name__ == "__main__":
    main()
