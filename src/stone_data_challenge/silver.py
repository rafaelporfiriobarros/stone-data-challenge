
import json
from datetime import datetime, timezone

import duckdb

from stone_data_challenge.config import (
    BRONZE_DIR,
    DATA_DIR,
    REPORTS_DIR,
)

SILVER_DIR = DATA_DIR / "silver"
QUARANTINE_DIR = DATA_DIR / "quarantine"

SCHEMAS = {
    "portfolio_geral": {
        "dates": [
            "dt_ref_portfolio", "safra",
            "dt_contrato", "dt_desembolso",
            "dt_vencimento", "dt_wo",
        ],
        "decimal": [
            "vlr_desembolsado", "vlr_tarifa",
            "juros_mes", "juros_diario",
            "perc_retencao", "vlr_pgto_realizado",
            "vlr_pgto_esperado", "vlr_saldo_devedor",
            "vlr_saldo_devedor_esperado",
        ],
        "integer": [
            "prazo", "dsp", "dspp",
            "flag_transacao",
        ],
        "required": [
            "contrato_id", "nr_documento",
            "dt_ref_portfolio",
        ],
    },
    "portfolio_tpv": {
        "dates": ["dt_transacao"],
        "decimal": ["vlr_tpv"],
        "integer": ["qtd_transacoes"],
        "required": ["nr_documento", "dt_transacao"],
    },
    "portfolio_comunicados": {
        "dates": ["dt_ref_portfolio", "data_acao"],
        "decimal": [],
        "integer": [],
        "required": ["contrato_id", "data_acao"],
    },
    "portfolio_clientes": {
        "dates": [],
        "decimal": [],
        "integer": [],
        "required": ["nr_documento"],
    },
}


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'



def expression(name, column, schema):
    col = quote(column)

    if column == "safra":
        return (
            f"TRY_STRPTIME("
            f"{col} || '-01', '%Y-%m-%d'"
            f")::DATE AS {col}"
        )

    if column in schema["dates"]:
        fmt = (
            "%Y%m%d"
            if name == "portfolio_tpv"
            else "%Y-%m-%d"
        )

        return (
            f"TRY_STRPTIME({col}, '{fmt}')"
            f"::DATE AS {col}"
        )

    if column in schema["decimal"]:
        return (
            f"TRY_CAST({col} AS DECIMAL(28, 8))"
            f" AS {col}"
        )

    if column in schema["integer"]:
        return (
            f"TRY_CAST({col} AS BIGINT) AS {col}"
        )

    return col



def build_dataset(con, name, schema):
    source = BRONZE_DIR / f"{name}.parquet"
    silver = SILVER_DIR / f"{name}.parquet"
    quarantine = QUARANTINE_DIR / f"{name}.parquet"

    if not source.exists():
        raise FileNotFoundError(source)

    columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(source)],
        ).fetchall()
    ]

    expected = set(
        schema["dates"]
        + schema["decimal"]
        + schema["integer"]
        + schema["required"]
    )

    missing = expected - set(columns)
    if missing:
        raise ValueError(
            f"{name}: colunas ausentes: {sorted(missing)}"
        )

    selections = [
        expression(name, column, schema)
        for column in columns
    ]

    # Materializa a conversão uma vez em tabela temporária.
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE typed AS
        SELECT {", ".join(selections)}
        FROM read_parquet(?)
        """,
        [str(source)],
    )

    typed_fields = (
        schema["dates"]
        + schema["decimal"]
        + schema["integer"]
    )

    invalid_conditions = [
        f"{quote(c)} IS NULL"
        for c in typed_fields
    ]

    invalid_conditions += [
        f"""(
            {quote(c)} IS NULL
            OR TRIM({quote(c)}) = ''
        )"""
        for c in schema["required"]
        if c not in typed_fields
    ]

    invalid_where = (
        " OR ".join(invalid_conditions)
        if invalid_conditions
        else "FALSE"
    )

    con.execute(
        f"""
        COPY (
            SELECT *
            FROM typed
            WHERE NOT ({invalid_where})
        )
        TO ?
        (FORMAT PARQUET, COMPRESSION ZSTD)
        """,
        [str(silver)],
    )

    con.execute(
        f"""
        COPY (
            SELECT *
            FROM typed
            WHERE {invalid_where}
        )
        TO ?
        (FORMAT PARQUET, COMPRESSION ZSTD)
        """,
        [str(quarantine)],
    )

    total = con.execute(
        "SELECT COUNT(*) FROM typed"
    ).fetchone()[0]

    accepted = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(silver)],
    ).fetchone()[0]

    rejected = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(quarantine)],
    ).fetchone()[0]

    assert total == accepted + rejected

    con.execute("DROP TABLE typed")

    print(
        f"[SILVER] {name}: "
        f"total={total:,}, "
        f"aceitos={accepted:,}, "
        f"quarentena={rejected:,}"
    )

    return {
        "dataset": name,
        "total": total,
        "accepted": accepted,
        "rejected": rejected,
    }


def main():
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    results = []

    try:
        for name, schema in SCHEMAS.items():
            results.append(
                build_dataset(con, name, schema)
            )

        report = {
            "executed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "datasets": results,
        }

        output = REPORTS_DIR / "silver_report.json"
        output.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        print("\n[OK] Silver construída")
        print(f"Relatório: {output}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
