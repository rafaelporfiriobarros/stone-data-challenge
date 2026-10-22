
import json

import duckdb

from stone_data_challenge.config import (
    BRONZE_DIR,
    REPORTS_DIR,
)


DATE_COLUMNS = {
    "portfolio_geral": [
        "dt_ref_portfolio",
        "dt_contrato",
        "dt_desembolso",
        "dt_vencimento",
        "dt_wo",
    ],
    "portfolio_tpv": ["dt_transacao"],
    "portfolio_comunicados": [
        "dt_ref_portfolio",
        "data_acao",
    ],
}

NUMERIC_COLUMNS = {
    "portfolio_geral": [
        "vlr_desembolsado",
        "vlr_pgto_realizado",
        "vlr_pgto_esperado",
        "vlr_saldo_devedor",
        "perc_retencao",
        "dsp",
        "dspp",
    ],
    "portfolio_tpv": [
        "qtd_transacoes",
        "vlr_tpv",
    ],
}

KEYS = {
    "portfolio_geral": [
        "contrato_id",
        "dt_ref_portfolio",
    ],
    "portfolio_tpv": [
        "nr_documento",
        "dt_transacao",
    ],
    "portfolio_clientes": ["nr_documento"],
}

CATEGORIES = {
    "portfolio_geral": [
        "status_contrato",
        "flag_transacao",
    ],
    "portfolio_comunicados": [
        "tipo_acao",
        "acao",
        "status",
    ],
    "portfolio_clientes": [
        "tipo_empresa",
        "segmento",
    ],
}


def path_for(name):
    path = BRONZE_DIR / f"{name}.parquet"
    if not path.is_file():
        raise FileNotFoundError(path)
    return str(path)


def sample_values(con, path, column):
    # Colunas são definidas em constantes internas.
    rows = con.execute(
        f"""
        SELECT DISTINCT "{column}"
        FROM read_parquet(?)
        WHERE "{column}" IS NOT NULL
        LIMIT 5
        """,
        [path],
    ).fetchall()

    return [row[0] for row in rows]


def analyze_keys(con, name, path):
    columns = KEYS.get(name)
    if not columns:
        return None

    keys = ", ".join(f'"{c}"' for c in columns)

    total, unique = con.execute(
        f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) AS unique_keys
        FROM (
            SELECT {keys}
            FROM read_parquet(?)
            GROUP BY {keys}
        )
        """,
        [path],
    ).fetchone()

    rows = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [path],
    ).fetchone()[0]

    result = {
        "key": columns,
        "rows": rows,
        "unique_keys": unique,
        "duplicate_excess": rows - unique,
    }

    print(f"\nCHAVE CANDIDATA: {columns}")
    print(f"  Linhas: {rows:,}")
    print(f"  Chaves distintas: {unique:,}")
    print(f"  Excesso de linhas: {rows - unique:,}")

    return result


def analyze_categories(con, name, path):
    result = {}

    for column in CATEGORIES.get(name, []):
        rows = con.execute(
            f"""
            SELECT "{column}", COUNT(*) AS n
            FROM read_parquet(?)
            GROUP BY "{column}"
            ORDER BY n DESC
            LIMIT 10
            """,
            [path],
        ).fetchall()

        result[column] = [
            {"value": value, "count": count}
            for value, count in rows
        ]

        print(f"\nCATEGORIAS: {column}")
        for value, count in rows:
            print(f"  {value}: {count:,}")

    return result


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '2GB'")

    report = {}

    try:
        datasets = [
            "portfolio_geral",
            "portfolio_tpv",
            "portfolio_comunicados",
            "portfolio_clientes",
        ]

        for name in datasets:
            path = path_for(name)

            print(f"\n{'=' * 60}")
            print(f"DATASET: {name}")
            print("=" * 60)

            dates = {}
            numbers = {}

            for column in DATE_COLUMNS.get(name, []):
                values = sample_values(
                    con, path, column
                )
                dates[column] = values
                print(f"\nDATA {column}: {values}")

            for column in NUMERIC_COLUMNS.get(name, []):
                values = sample_values(
                    con, path, column
                )
                numbers[column] = values
                print(f"\nNUMÉRICO {column}: {values}")

            keys = analyze_keys(con, name, path)
            categories = analyze_categories(
                con, name, path
            )

            report[name] = {
                "date_samples": dates,
                "numeric_samples": numbers,
                "keys": keys,
                "categories": categories,
            }

        output = REPORTS_DIR / "schema_analysis.json"

        output.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        print("\n[OK] Análise estrutural concluída")
        print(f"Relatório: {output}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
