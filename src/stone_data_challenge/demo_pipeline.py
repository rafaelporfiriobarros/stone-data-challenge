
import argparse
import json
from pathlib import Path

import duckdb

from stone_data_challenge.synthetic_demo import (
    generate_synthetic_data,
)


def run_demo(
    output_dir: Path,
    n_contracts: int = 100,
    seed: int = 42,
) -> dict:
    output_dir = Path(output_dir)
    source_dir = output_dir / "source"
    bronze_dir = output_dir / "bronze"
    silver_dir = output_dir / "silver"
    gold_dir = output_dir / "gold"

    for directory in [
        source_dir,
        bronze_dir,
        silver_dir,
        gold_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    sources = generate_synthetic_data(
        source_dir,
        n_contracts=n_contracts,
        seed=seed,
    )

    con = duckdb.connect()

    try:
        # Bronze: ingestão sem regras de negócio.
        for name, source_path in sources.items():
            con.execute(
                f"""
                CREATE OR REPLACE TABLE bronze_{name} AS
                SELECT *
                FROM read_csv_auto(
                    ?,
                    header = true,
                    all_varchar = true
                )
                """,
                [str(source_path)],
            )

            con.execute(
                f"""
                COPY bronze_{name}
                TO '{(bronze_dir / (name + ".parquet")).as_posix()}'
                (FORMAT PARQUET)
                """
            )

        # Silver: conversão explícita de tipos.
        con.execute("""
            CREATE TABLE silver_contracts AS
            SELECT
                contrato_id,
                cliente_id,
                CAST(data_contrato AS DATE) AS data_contrato,
                CAST(vlr_desembolsado AS DECIMAL(18,2))
                    AS vlr_desembolsado,
                CAST(prazo AS INTEGER) AS prazo,
                CAST(perc_retencao AS DOUBLE)
                    AS perc_retencao
            FROM bronze_contracts
        """)

        con.execute("""
            CREATE TABLE silver_payments AS
            SELECT
                contrato_id,
                CAST(data_pagamento AS DATE)
                    AS data_pagamento,
                CAST(valor_pagamento AS DECIMAL(18,2))
                    AS valor_pagamento
            FROM bronze_payments
        """)

        con.execute("""
            CREATE TABLE silver_campaigns AS
            SELECT
                contrato_id,
                CAST(data_acao AS DATE) AS data_acao,
                acao
            FROM bronze_campaigns
        """)

        for name in ["contracts", "payments", "campaigns"]:
            con.execute(
                f"""
                COPY silver_{name}
                TO '{(silver_dir / (name + ".parquet")).as_posix()}'
                (FORMAT PARQUET)
                """
            )

        # Integridade referencial.
        for table in ["silver_payments", "silver_campaigns"]:
            invalid = con.execute(f"""
                SELECT COUNT(*)
                FROM {table} AS t
                LEFT JOIN silver_contracts AS c
                    ON t.contrato_id = c.contrato_id
                WHERE c.contrato_id IS NULL
            """).fetchone()[0]

            if invalid:
                raise ValueError(
                    f"{table}: {invalid} contratos inexistentes"
                )

        # Gold: uma linha por contrato.
        con.execute("""
            CREATE TABLE gold_contract_summary AS
            WITH payments AS (
                SELECT
                    contrato_id,
                    COUNT(*) AS payment_days,
                    SUM(valor_pagamento) AS total_paid,
                    COUNT(*) FILTER (
                        WHERE valor_pagamento > 0
                    ) AS positive_payment_days
                FROM silver_payments
                GROUP BY contrato_id
            ),
            campaigns AS (
                SELECT
                    contrato_id,
                    COUNT(*) AS total_campaigns
                FROM silver_campaigns
                GROUP BY contrato_id
            )
            SELECT
                c.contrato_id,
                c.cliente_id,
                c.vlr_desembolsado,
                c.prazo,
                c.perc_retencao,
                p.payment_days,
                p.total_paid,
                p.positive_payment_days,
                COALESCE(a.total_campaigns, 0)
                    AS total_campaigns
            FROM silver_contracts AS c
            LEFT JOIN payments AS p
                ON c.contrato_id = p.contrato_id
            LEFT JOIN campaigns AS a
                ON c.contrato_id = a.contrato_id
        """)

        gold_path = gold_dir / "contract_summary.parquet"

        con.execute(
            f"""
            COPY gold_contract_summary
            TO '{gold_path.as_posix()}'
            (FORMAT PARQUET)
            """
        )

        result = con.execute("""
            SELECT
                COUNT(*) AS contracts,
                SUM(payment_days) AS payment_rows,
                SUM(total_campaigns) AS campaigns,
                SUM(total_paid) AS total_paid
            FROM gold_contract_summary
        """).fetchone()

        # Reconciliação dos valores de pagamento.
        source_total = con.execute("""
            SELECT SUM(valor_pagamento)
            FROM silver_payments
        """).fetchone()[0]

        if result[3] != source_total:
            raise ValueError(
                "Falha na reconciliação financeira"
            )

        if result[0] != n_contracts:
            raise ValueError(
                "Quantidade de contratos inconsistente"
            )

        report = {
            "status": "SUCCESS",
            "data_type": "SYNTHETIC",
            "contracts": result[0],
            "payment_rows": result[1],
            "campaigns": result[2],
            "total_paid": float(result[3]),
            "financial_reconciliation": True,
            "gold_path": str(gold_path),
        }

        report_path = output_dir / "demo_report.json"
        report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        return report

    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/demo"),
    )
    parser.add_argument(
        "--contracts",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    report = run_demo(
        output_dir=args.output,
        n_contracts=args.contracts,
        seed=args.seed,
    )

    print("\nSTONE | SYNTHETIC DEMO")
    print("=" * 50)
    print(json.dumps(report, indent=2))
    print("\n[OK] Demo executada")


if __name__ == "__main__":
    main()
