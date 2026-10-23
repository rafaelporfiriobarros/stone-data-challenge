
from pathlib import Path

import duckdb


DATASET = Path("data/analytics/contrato_observacao_7d_v2.parquet")
OUTPUT = Path("reports/business_analysis")


def main() -> None:
    if not DATASET.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {DATASET}")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.read_parquet(str(DATASET.resolve())).create_view("observacoes")

    query = """
        WITH base AS (
            SELECT
                contrato_id,
                data_observacao,
                target_pagamento_7d,
                DATE_TRUNC('quarter', data_observacao)
                    AS trimestre,

                CASE
                    WHEN campanhas_30d = 0
                        THEN '01. Nenhuma'
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
            trimestre,
            faixa_campanhas,
            COUNT(*) AS observacoes,
            COUNT(DISTINCT contrato_id) AS contratos,
            SUM(target_pagamento_7d) AS positivos,
            ROUND(
                100.0 * AVG(target_pagamento_7d),
                2
            ) AS taxa_indicador_pct

        FROM base
        GROUP BY trimestre, faixa_campanhas
        ORDER BY trimestre, faixa_campanhas
    """

    result = con.execute(query).fetchdf()
    destination = OUTPUT / "robustez_temporal.csv"

    result.to_csv(destination, index=False)

    print("\n=== ROBUSTEZ TEMPORAL POR TRIMESTRE ===")
    print(result.to_string(index=False))
    print(f"\nArquivo gerado: {destination}")

    con.close()


if __name__ == "__main__":
    main()
