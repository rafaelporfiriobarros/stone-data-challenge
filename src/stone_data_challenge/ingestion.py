
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from stone_data_challenge.config import (
    BRONZE_DIR,
    DATASETS,
    DATABASE_PATH,
    RAW_DIR,
    REPORTS_DIR,
    WAREHOUSE_DIR,
)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(8 * 1024 * 1024), b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def ingest_dataset(
    con: duckdb.DuckDBPyConnection,
    name: str,
    filename: str,
) -> dict:
    source = RAW_DIR / filename
    destination = BRONZE_DIR / f"{name}.parquet"

    if not source.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {source}"
        )

    print(f"\n[INGESTÃO] {name}")

    source_hash = file_hash(source)

    # Primeira etapa: preservar os valores como texto.
    # Tipagem de negócio será feita na camada Silver.
    con.execute(
        """
        COPY (
            SELECT *
            FROM read_csv(
                ?,
                header = true,
                all_varchar = true,
                auto_detect = true,
                sample_size = -1
            )
        )
        TO ?
        (FORMAT PARQUET, COMPRESSION ZSTD)
        """,
        [str(source), str(destination)],
    )

    total = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(destination)],
    ).fetchone()[0]

    metadata = {
        "dataset": name,
        "source": filename,
        "source_sha256": source_hash,
        "source_bytes": source.stat().st_size,
        "bronze_bytes": destination.stat().st_size,
        "rows": total,
        "ingested_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    print(f"[OK] {total:,} registros")
    return metadata


def main() -> None:
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DATABASE_PATH))

    try:
        con.execute("SET threads = 4")
        con.execute("SET memory_limit = '2GB'")

        results = []

        for name, filename in DATASETS.items():
            metadata = ingest_dataset(
                con, name, filename
            )
            results.append(metadata)

        report_path = REPORTS_DIR / "ingestion_report.json"

        report_path.write_text(
            json.dumps(
                results,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print("\n[OK] Ingestão concluída")
        print(f"Relatório: {report_path}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
