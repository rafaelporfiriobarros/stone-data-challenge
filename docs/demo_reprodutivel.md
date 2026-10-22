# Reproducible Synthetic Demo

## Purpose

This demonstration validates a simplified Bronze → Silver → Gold data pipeline using entirely synthetic data.

It does not require access to the original Stone Data Challenge datasets.

## Requirements

- Python 3.12
- UV
- DuckDB
- pytest

## Run

```powershell
uv sync
uv run python -m stone_data_challenge.demo_pipeline --output data/demo --contracts 100 --seed 42
uv run pytest tests/test_demo_pipeline.py -v
```

## Outputs

- `data/demo/source/`: synthetic CSV files
- `data/demo/bronze/`: raw Parquet data
- `data/demo/silver/`: typed Parquet data
- `data/demo/gold/`: aggregated contract-level data
- `data/demo/demo_report.json`: execution and reconciliation summary

## Validation

The demonstration verifies:

- Deterministic data generation
- Contract identifier integrity
- Payment value reconciliation
- Unique contract keys in Gold
- Valid references between campaigns and contracts
- Successful generation of output artifacts

## Scope and limitations

This is an independent demonstration of the data engineering architecture.

It does not reproduce the original financial data distributions, historical features, supervised target, trained models, or model governance evaluations.

The full project test suite requires the original local artifacts and is not executed in public CI.