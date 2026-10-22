
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BRONZE_DIR = DATA_DIR / "bronze"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
REPORTS_DIR = PROJECT_ROOT / "reports"

DATABASE_PATH = WAREHOUSE_DIR / "stone.duckdb"

DATASETS = {
    "portfolio_geral": "portfolio_geral.csv",
    "portfolio_tpv": "portfolio_tpv.csv",
    "portfolio_comunicados": "portfolio_comunicados.csv",
    "portfolio_clientes": "portfolio_clientes.csv",
}
