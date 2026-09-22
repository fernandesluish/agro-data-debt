from pathlib import Path

import duckdb
import polars as pl
import requests

API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"

def fetch_municipios() -> list[dict]:
    """Call the IBGE API and return the flattened list of municipalities."""
    response = requests.get(API_URL, params={"view": "nivelado"}, timeout=60)
    response.raise_for_status()
    return response.json()


def save_raw_file(records: list[dict]) -> Path:
    """Persist the API payload as a parquet file, untouched."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(records)
    output_path = RAW_DIR / "ibge_municipios.parquet"
    df.write_parquet(output_path)
    return output_path


def load_to_duckdb(parquet_path: Path) -> int:
    """Load the parquet file into the raw schema of the warehouse."""
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        """
        CREATE OR REPLACE TABLE raw.ibge_municipios AS
        SELECT * FROM read_parquet(?)
        """,
        [str(parquet_path)],
    )
    row_count = con.execute("Select count(*) FROM raw.ibge_municipios").fetchone()[0]
    con.close()
    return row_count


def main() -> None:
    print("Fetching municipalities from IBGE API...")
    records = fetch_municipios()
    print(f"Fetched {len(records)} records.")

    parquet_path = save_raw_file(records)
    print(f"Saved raw data to {parquet_path}.")

    row_count = load_to_duckdb(parquet_path)
    print(f"Loaded {row_count} records into DuckDB at {DB_PATH}.")


if __name__ == "__main__":
    main()