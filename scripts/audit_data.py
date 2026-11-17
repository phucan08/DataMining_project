"""Profile the raw workbook; this script reports issues and never cleans raw data."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COLUMNS = [
    "InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"
]


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(input_path: Path, output_dir: Path) -> dict:
    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError("pandas is not installed. Run scripts/setup.ps1 first.") from error
    if not input_path.is_file():
        raise FileNotFoundError(f"Raw workbook not found: {input_path}. Run scripts/download_data.py first.")
    input_hash = file_sha256(input_path)
    data = pd.read_excel(
        input_path,
        engine="openpyxl",
        dtype={"InvoiceNo": "string", "StockCode": "string", "CustomerID": "string"},
    )
    missing_columns = sorted(set(EXPECTED_COLUMNS) - set(data.columns))
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")
    if data.empty:
        raise ValueError("The raw workbook contains no transaction rows.")
    dates = pd.to_datetime(data["InvoiceDate"], errors="coerce")
    quantity = pd.to_numeric(data["Quantity"], errors="coerce")
    price = pd.to_numeric(data["UnitPrice"], errors="coerce")
    cancelled = data["InvoiceNo"].str.upper().str.startswith("C", na=False)
    missing = data.isna().sum()
    invoice_groups = data.groupby("InvoiceNo", dropna=True)
    invoice_customers = invoice_groups["CustomerID"].nunique(dropna=True)
    invoice_dates = data.assign(parsed_date=dates).groupby("InvoiceNo")["parsed_date"].nunique()
    observed = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_path.resolve()),
        "input_sha256": input_hash,
        "status": "raw_observed_not_cleaned",
        "rows": int(len(data)),
        "columns": list(data.columns),
        "additional_columns": sorted(set(data.columns) - set(EXPECTED_COLUMNS)),
        "distinct_invoice_ids": int(data["InvoiceNo"].nunique()),
        "distinct_product_ids": int(data["StockCode"].nunique()),
        "distinct_identified_customer_ids": int(data["CustomerID"].nunique()),
        "distinct_countries": int(data["Country"].nunique()),
        "date_min": None if dates.isna().all() else dates.min().isoformat(),
        "date_max": None if dates.isna().all() else dates.max().isoformat(),
        "missing_by_column": {str(k): int(v) for k, v in missing.items()},
        "exact_duplicate_rows_after_first": int(data.duplicated().sum()),
        "repeated_invoice_product_rows_after_first": int(data.duplicated(subset=["InvoiceNo", "StockCode"]).sum()),
        "product_ids_with_multiple_nonmissing_descriptions": int((data.groupby("StockCode")["Description"].nunique() > 1).sum()),
        "cancelled_invoice_rows": int(cancelled.sum()),
        "quantity_negative_rows": int((quantity < 0).sum()),
        "quantity_zero_rows": int((quantity == 0).sum()),
        "unit_price_negative_rows": int((price < 0).sum()),
        "unit_price_zero_rows": int((price == 0).sum()),
        "invalid_nonmissing_dates": int((dates.isna() & data["InvoiceDate"].notna()).sum()),
        "invalid_nonmissing_quantity": int((quantity.isna() & data["Quantity"].notna()).sum()),
        "invalid_nonmissing_unit_price": int((price.isna() & data["UnitPrice"].notna()).sum()),
        "invoice_ids_with_multiple_nonmissing_customers": int((invoice_customers > 1).sum()),
        "invoice_ids_with_multiple_timestamps": int((invoice_dates > 1).sum()),
        "notes": [
            "Issue counts overlap and must not be added to estimate removed rows.",
            "Cancelled invoice IDs are included in raw invoice counts.",
            "No rows were removed; no country, time split, or cleaning thresholds were selected.",
            "Date timestamps are reported as stored; source timezone has not been inferred.",
        ],
    }
    monthly = (
        data.assign(month=dates.dt.strftime("%Y-%m"))
        .groupby("month", dropna=False)
        .agg(rows=("InvoiceNo", "size"), invoices=("InvoiceNo", "nunique"))
        .reset_index()
    )
    schema = pd.DataFrame([
        {"column": column, "dtype": str(data[column].dtype), "missing": int(missing[column]), "unique_nonmissing": int(data[column].nunique())}
        for column in data.columns
    ])
    countries = (
        data.groupby("Country", dropna=False)
        .agg(rows=("InvoiceNo", "size"), invoices=("InvoiceNo", "nunique"), identified_customers=("CustomerID", "nunique"))
        .sort_values("rows", ascending=False)
        .reset_index()
    )
    numeric_summary = pd.DataFrame({"Quantity": quantity, "UnitPrice": price, "RawLineValue": quantity * price}).describe(
        percentiles=[0.01, 0.25, 0.5, 0.75, 0.95, 0.99]
    )
    if file_sha256(input_path) != input_hash:
        raise RuntimeError("Raw workbook changed during the audit; results were not saved.")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "raw_audit.json").write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8")
    schema.to_csv(output_dir / "raw_schema.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(output_dir / "raw_monthly_counts.csv", index=False, encoding="utf-8-sig")
    countries.to_csv(output_dir / "raw_country_counts.csv", index=False, encoding="utf-8-sig")
    numeric_summary.to_csv(output_dir / "raw_numeric_summary.csv", index_label="statistic", encoding="utf-8-sig")
    return observed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "raw" / "Online Retail.xlsx")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "tables")
    args = parser.parse_args()
    try:
        result = audit(args.input.resolve(), args.output_dir.resolve())
    except (RuntimeError, FileNotFoundError, ValueError) as error:
        parser.exit(1, f"Audit could not run: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
