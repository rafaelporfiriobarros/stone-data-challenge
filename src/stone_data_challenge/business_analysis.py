
from pathlib import Path
import duckdb

DATASET = Path("data/analytics/contrato_observacao_7d_v2.parquet")
OUTPUT = Path("reports/business_analysis")


def main() -> None:
    if not DATASET.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {DATASET}")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    path = str(DATASET.resolve())

    con.execute(
        """
        CREATE TEMP VIEW observacoes AS
        SELECT *
        FROM read_parquet('data/analytics/contrato_observacao_7d_v2.parquet')
        """
    )

    queries = {
        "perfil_geral": """
            SELECT
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,
                SUM(CASE WHEN target_pagamento_7d = 1 THEN 1 ELSE 0 END)
                    AS observacoes_positivas,
                ROUND(100.0 * AVG(target_pagamento_7d), 2)
                    AS taxa_indicador_pct,
                MIN(data_observacao) AS primeira_data,
                MAX(data_observacao) AS ultima_data
            FROM observacoes
        """,

        "pagamento_por_valor": """
            WITH base AS (
                SELECT *,
                    CASE
                        WHEN vlr_desembolsado < 2000 THEN '01. Abaixo de 2 mil'
                        WHEN vlr_desembolsado < 5000 THEN '02. De 2 a 5 mil'
                        WHEN vlr_desembolsado < 10000 THEN '03. De 5 a 10 mil'
                        WHEN vlr_desembolsado >= 10000 THEN '04. Acima de 10 mil'
                        ELSE '05. Não informado'
                    END AS faixa_valor
                FROM observacoes
            )
            SELECT
                faixa_valor,
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,
                ROUND(100.0 * AVG(target_pagamento_7d), 2)
                    AS taxa_indicador_pct
            FROM base
            GROUP BY faixa_valor
            ORDER BY faixa_valor
        """,

        "pagamento_por_prazo": """
            WITH base AS (
                SELECT *,
                    CASE
                        WHEN prazo <= 12 THEN '01. Até 12 meses'
                        WHEN prazo <= 24 THEN '02. De 13 a 24 meses'
                        WHEN prazo <= 36 THEN '03. De 25 a 36 meses'
                        WHEN prazo > 36 THEN '04. Acima de 36 meses'
                        ELSE '05. Não informado'
                    END AS faixa_prazo
                FROM observacoes
            )
            SELECT
                faixa_prazo,
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,
                ROUND(100.0 * AVG(target_pagamento_7d), 2)
                    AS taxa_indicador_pct
            FROM base
            GROUP BY faixa_prazo
            ORDER BY faixa_prazo
        """,

        "pagamento_por_campanhas": """
            WITH base AS (
                SELECT *,
                    CASE
                        WHEN campanhas_30d = 0 THEN '01. Nenhuma'
                        WHEN campanhas_30d = 1 THEN '02. Uma'
                        WHEN campanhas_30d BETWEEN 2 AND 3 THEN '03. Duas a três'
                        WHEN campanhas_30d >= 4 THEN '04. Quatro ou mais'
                        ELSE '05. Não informado'
                    END AS faixa_campanhas
                FROM observacoes
            )
            SELECT
                faixa_campanhas,
                COUNT(*) AS observacoes,
                COUNT(DISTINCT contrato_id) AS contratos,
                ROUND(100.0 * AVG(target_pagamento_7d), 2)
                    AS taxa_indicador_pct
            FROM base
            GROUP BY faixa_campanhas
            ORDER BY faixa_campanhas
        """,
    }

    for name, sql in queries.items():
        result = con.execute(sql).fetchdf()
        result.to_csv(OUTPUT / f"{name}.csv", index=False)

        print(f"\n=== {name.upper()} ===")
        print(result.to_string(index=False))

    con.close()
    print("\nAnálise concluída.")


if __name__ == "__main__":
    main()
