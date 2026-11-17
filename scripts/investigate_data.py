"""Investigate anomalies without deleting, imputing, or overwriting raw records."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_io import COLUMNS, read_verified_raw, verify_raw_unchanged


def investigate(data: pd.DataFrame, output: Path, raw_hash: str) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    frame = data.copy()
    frame["SourceRow"] = range(2, len(frame) + 2)
    cancelled = frame["InvoiceNo"].str.upper().str.startswith("C", na=False)
    positive = ~cancelled & frame["Quantity"].gt(0) & frame["UnitPrice"].gt(0)
    invoice = frame.groupby("InvoiceNo").agg(
        rows=("StockCode", "size"), timestamps=("InvoiceDate", "nunique"),
        first_time=("InvoiceDate", "min"), last_time=("InvoiceDate", "max"),
        known_customer_ids=("CustomerID", "nunique"), countries=("Country", "nunique"),
    ).reset_index()
    invoice["span_minutes"] = (invoice["last_time"] - invoice["first_time"]).dt.total_seconds() / 60
    changed_times = invoice.loc[invoice["timestamps"] > 1].copy()
    changed_times.to_csv(output / "anomaly_invoice_timestamps.csv", index=False)

    nonstandard = ~frame["StockCode"].str.fullmatch(r"\d{5}[A-Za-z]*", na=False)
    suspect_codes = frame.loc[nonstandard].copy()
    suspect_codes["cancelled"] = cancelled.loc[nonstandard]
    suspect_codes["quantity_negative"] = suspect_codes["Quantity"] < 0
    suspect_codes["price_nonpositive"] = suspect_codes["UnitPrice"] <= 0
    suspect_codes["positive_purchase"] = positive.loc[nonstandard]
    suspect_codes["line_value"] = suspect_codes["Quantity"] * suspect_codes["UnitPrice"]
    code_profile = suspect_codes.groupby("StockCode").agg(
        rows=("SourceRow", "size"), invoices=("InvoiceNo", "nunique"),
        cancelled_rows=("cancelled", "sum"), negative_quantity_rows=("quantity_negative", "sum"),
        nonpositive_price_rows=("price_nonpositive", "sum"), positive_purchase_rows=("positive_purchase", "sum"),
        raw_line_value=("line_value", "sum"),
    )
    descriptions = suspect_codes.groupby("StockCode")["Description"].agg(
        lambda values: " || ".join(values.dropna().astype(str).value_counts().head(5).index)
    )
    code_profile = code_profile.join(descriptions.rename("observed_descriptions")).reset_index().sort_values("rows", ascending=False)
    code_profile.to_csv(output / "anomaly_nonstandard_stockcodes.csv", index=False)

    samples = []
    conditions = {
        "noncancel_negative_quantity": ~cancelled & frame["Quantity"].lt(0),
        "negative_price": frame["UnitPrice"].lt(0),
        "zero_price": frame["UnitPrice"].eq(0),
        "positive_missing_description": positive & frame["Description"].isna(),
    }
    for issue, mask in conditions.items():
        subset = frame.loc[mask].head(20).copy()
        subset.insert(0, "Issue", issue)
        samples.append(subset)
    pd.concat(samples, ignore_index=True).to_csv(output / "anomaly_row_samples.csv", index=False)
    duplicate = frame.duplicated(subset=COLUMNS, keep="first")
    frame.loc[duplicate].head(30).to_csv(output / "anomaly_duplicate_samples.csv", index=False)

    product_names = frame.loc[positive & frame["Description"].notna()].groupby(["StockCode", "Description"]).agg(
        rows=("SourceRow", "size"), invoices=("InvoiceNo", "nunique")
    ).reset_index()
    ambiguous_ids = product_names.groupby("StockCode")["Description"].nunique()
    product_names.loc[product_names["StockCode"].isin(ambiguous_ids[ambiguous_ids > 1].index)].to_csv(
        output / "anomaly_description_variants.csv", index=False
    )
    positive_data = frame.loc[positive].copy()
    positive_data["line_value"] = positive_data["Quantity"] * positive_data["UnitPrice"]
    positive_data.nlargest(20, "line_value").to_csv(output / "anomaly_largest_purchase_lines.csv", index=False)
    positive_data.nlargest(20, "Quantity").to_csv(output / "anomaly_largest_quantities.csv", index=False)

    customer_pattern = frame.assign(known_id=frame["CustomerID"].notna()).groupby("InvoiceNo")["known_id"].agg(["any", "all"])
    summary = {
        "raw_sha256": raw_hash,
        "rows": len(frame),
        "nonstandard_stockcodes": len(code_profile),
        "nonstandard_stockcode_rows": int(nonstandard.sum()),
        "nonstandard_positive_purchase_rows": int((nonstandard & positive).sum()),
        "noncancel_negative_quantity_rows": int((~cancelled & frame["Quantity"].lt(0)).sum()),
        "positive_purchase_rows_before_other_filters": int(positive.sum()),
        "positive_purchase_rows_missing_description": int((positive & frame["Description"].isna()).sum()),
        "positive_purchase_rows_missing_customer_id": int((positive & frame["CustomerID"].isna()).sum()),
        "positive_purchase_exact_duplicates_after_first": int((positive & duplicate).sum()),
        "duplicate_positive_purchase_value_gbp": round(float((frame.loc[positive & duplicate, "Quantity"] * frame.loc[positive & duplicate, "UnitPrice"]).sum()), 2),
        "invoice_ids_with_multiple_times": len(changed_times),
        "max_invoice_span_minutes": float(changed_times["span_minutes"].max()) if len(changed_times) else 0,
        "multi_time_invoices_crossing_calendar_dates": int((changed_times["first_time"].dt.normalize() != changed_times["last_time"].dt.normalize()).sum()),
        "invoice_ids_with_multiple_known_customers": int((invoice["known_customer_ids"] > 1).sum()),
        "invoice_ids_with_multiple_countries": int((invoice["countries"] > 1).sum()),
        "invoice_ids_with_partially_missing_customer": int((customer_pattern["any"] & ~customer_pattern["all"]).sum()),
        "invoice_ids_without_any_known_customer": int((~customer_pattern["any"]).sum()),
        "positive_purchase_product_ids_with_description_variants": int((ambiguous_ids > 1).sum()),
        "no_rows_cleaned": True,
    }
    (output / "anomaly_investigation.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    data, digest = read_verified_raw(ROOT)
    result = investigate(data, ROOT / "results/tables", digest)
    verify_raw_unchanged(ROOT, digest)
    print(json.dumps(result, indent=2))
