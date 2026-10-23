
from pathlib import Path

import duckdb


DATASET = Path("data/analytics/contrato_observacao_7d_v2.parquet")
OUTPUT = Path("reports/business_analysis")


def main() -> None:
    if not DATASET.exists():
        raise FileNotFoundError(DATASET)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    # Relação registrada sem interpolar caminhos em SQL.
    con.read_parquet(str(DATASET.resolve())).create_view("observacoes")

    query = """
        WITH segmentada AS (
            SELECT
                contrato_id,
                data_observacao,
                target_pagamento_7d,

                CASE
                    WHEN vlr_desembolsado < 5000
                        THEN '01. Menos de 5 mil'
                    WHEN vlr_desembolsado < 10000
                        THEN '02. De 5 a 10 mil'
                    WHEN vlr_desembolsado >= 10000
                        THEN '03. 10 mil ou mais'
                    ELSE '04. Não informado'
                END AS faixa_valor,

                CASE
                    WHEN prazo <= 24 THEN '01. Até 24 meses'
                    WHEN prazo > 24 THEN '02. Acima de 24 meses'
                    ELSE '03. Não informado'
                END AS faixa_prazo,

                CASE
                    WHEN campanhas_30d = 0 THEN '01. Nenhuma'
                    WHEN campanhas_30d BETWEEN 1 AND 3
                        THEN '02. De 1 a 3'
                    WHEN campanhas_30d >= 4
                        THEN '03. Quatro ou mais'
                    ELSE '04. Não informado'
                END AS faixa_campanhas

            FROM observacoes
            WHERE target_pagamento_7d IN (0, 1)
        )

        SELECT
            faixa_valor,
            faixa_prazo,
            faixa_campanhas,
            COUNT(*) AS observacoes,
            COUNT(DISTINCT contrato_id) AS contratos,
            SUM(target_pagamento_7d) AS positivos,
            ROUND(
                100.0 * AVG(target_pagamento_7d),
                2
            ) AS taxa_indicador_pct

        FROM segmentada
        GROUP BY
            faixa_valor,
            faixa_prazo,
            faixa_campanhas

        ORDER BY
            faixa_valor,
            faixa_prazo,
            faixa_campanhas
    """

    result = con.execute(query).fetchdf()

    destination = OUTPUT / "pagamento_segmentado.csv"
    result.to_csv(destination, index=False)

    print("\n=== ANÁLISE SEGMENTADA ===")
    print(result.to_string(index=False))
    print(f"\nArquivo gerado: {destination}")

    con.close()


if __name__ == "__main__":
    main()
