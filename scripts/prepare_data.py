"""Run the reviewed cleaning policy and build basket/RFM datasets."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_io import read_verified_raw, sha256, verify_raw_unchanged
from src.preprocessing import clean_purchase_lines, fit_train_catalog, make_baskets, make_rfm, save_sparse_baskets
from investigate_data import investigate


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    options = {"compression": {"method": "gzip", "mtime": 0}} if path.suffix == ".gz" else {}
    frame.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S", **options)


def return_evidence(raw: pd.DataFrame, clean: pd.DataFrame, output: Path) -> int:
    negatives = raw.loc[raw["Quantity"].lt(0)].copy()
    negatives["SourceRow"] = negatives.index + 2
    evidence = []
    for purchase in clean.nlargest(10, "Quantity").itertuples(index=False):
        if pd.isna(purchase.CustomerID):
            continue
        matches = negatives.loc[
            negatives["StockCode"].eq(purchase.StockCode)
            & negatives["CustomerID"].eq(purchase.CustomerID)
            & negatives["Quantity"].eq(-purchase.Quantity)
            & negatives["UnitPrice"].eq(purchase.UnitPrice)
            & negatives["InvoiceDate"].ge(purchase.InvoiceDate)
        ].sort_values("InvoiceDate").head(1)
        for returned in matches.itertuples(index=False):
            evidence.append({
                "PurchaseSourceRow": purchase.SourceRow, "PurchaseInvoiceNo": purchase.InvoiceNo,
                "ReturnSourceRow": returned.SourceRow, "ReturnInvoiceNo": returned.InvoiceNo,
                "StockCode": purchase.StockCode, "CustomerID": purchase.CustomerID, "Quantity": purchase.Quantity,
                "PurchaseTimestamp": purchase.InvoiceDate, "ReturnTimestamp": returned.InvoiceDate,
                "MinutesUntilReturn": (returned.InvoiceDate - purchase.InvoiceDate).total_seconds() / 60,
                "PurchaseValueGBP": purchase.PurchaseValueGBP,
            })
    columns = ["PurchaseSourceRow", "PurchaseInvoiceNo", "ReturnSourceRow", "ReturnInvoiceNo", "StockCode", "CustomerID", "Quantity", "PurchaseTimestamp", "ReturnTimestamp", "MinutesUntilReturn", "PurchaseValueGBP"]
    pd.DataFrame(evidence, columns=columns).to_csv(output / "anomaly_extreme_purchase_return_evidence.csv", index=False)
    return len(evidence)


def main() -> None:
    policy_path = ROOT / "configs/cleaning_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    data_dir = ROOT / "data/processed"
    tables = ROOT / "results/tables"
    data_dir.mkdir(parents=True, exist_ok=True)
    print("Reading and verifying raw workbook...", flush=True)
    raw, raw_hash = read_verified_raw(ROOT)
    investigate(raw, tables, raw_hash)
    print("Applying reviewed cleaning policy...", flush=True)
    clean, excluded, log, summary = clean_purchase_lines(raw, policy)
    if summary["unreviewed_positive_stock_codes"]:
        raise RuntimeError("Unreviewed positive-product codes remain; inspect the investigation before finalizing outputs.")
    baskets, items = make_baskets(clean, policy)
    catalog = fit_train_catalog(clean)
    rfm, features, transform = make_rfm(baskets, policy)
    items["KnownTrainProduct"] = items["StockCode"].isin(catalog["StockCode"])
    prior_customer_ids = set(rfm["CustomerID"])
    baskets["HasTrainCustomerProfile"] = baskets["CustomerID"].isin(prior_customer_ids)
    clean_train = clean.loc[clean["Split"].eq("train")]
    cutoff = pd.Timestamp(policy["rfm_reference_date"])
    assert clean_train["InvoiceDate"].lt(cutoff).all(), "Future source lines entered train."
    assert clean.groupby("InvoiceNo")["Split"].nunique().max() == 1
    eligible_train = baskets.loc[baskets["Split"].eq("train") & baskets["FullyIdentified"]]
    assert int(rfm["MonetaryMicroGBP"].sum()) == int(eligible_train["PurchaseValueMicroGBP"].sum())
    assert len(items) == int(baskets["UniqueProducts"].sum())
    assert len(clean) + int(log["rows_removed"].sum()) == len(raw)

    write_csv(clean, data_dir / "purchase_lines.csv.gz")
    write_csv(excluded, data_dir / "excluded_lines.csv.gz")
    returns = raw.loc[raw["InvoiceNo"].str.upper().str.startswith("C", na=False) | raw["Quantity"].le(0) | raw["UnitPrice"].le(0)].copy()
    returns.insert(0, "SourceRow", returns.index + 2)
    write_csv(returns, data_dir / "returns_adjustments_raw.csv.gz")
    write_csv(baskets, data_dir / "baskets.csv")
    write_csv(items, data_dir / "basket_items.csv.gz")
    write_csv(catalog, data_dir / "product_catalog_train.csv")
    write_csv(rfm, data_dir / "rfm_train.csv")
    write_csv(features, data_dir / "rfm_train_features.csv")
    (data_dir / "rfm_transform.json").write_text(json.dumps(transform, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    matrices = save_sparse_baskets(baskets, items, catalog, data_dir)
    log.to_csv(tables / "cleaning_log.csv", index=False)

    cohorts = []
    for split in ["train", "validation", "test"]:
        invoices = baskets.loc[baskets["Split"].eq(split)]
        lines = clean.loc[clean["Split"].eq(split)]
        cohorts.append({
            "split": split, "purchase_lines": len(lines), "invoices": len(invoices), "product_ids": int(lines["StockCode"].nunique()),
            "identified_customers": int(invoices["CustomerID"].nunique()), "identified_invoices": int(invoices["FullyIdentified"].sum()),
            "single_item_baskets": int(invoices["SingleItemBasket"].sum()),
            "new_identified_customer_ids_vs_train": int(invoices.loc[invoices["CustomerID"].notna() & ~invoices["HasTrainCustomerProfile"], "CustomerID"].nunique()),
            "invoices_with_no_train_customer_profile": int((~invoices["HasTrainCustomerProfile"]).sum()),
        })
    pd.DataFrame(cohorts).to_csv(tables / "prepared_cohort_summary.csv", index=False)
    rfm[["Recency", "Frequency", "Monetary"]].describe(percentiles=[0.5, 0.95, 0.99]).to_csv(tables / "rfm_train_summary.csv", index_label="statistic")

    # Reconcile sample RFM values directly from cleaned source lines, not from basket aggregation.
    sample_ids = list(dict.fromkeys(rfm.head(3)["CustomerID"].tolist() + rfm.nlargest(2, "Monetary")["CustomerID"].tolist()))
    checks = []
    for customer_id in sample_ids:
        lines = clean_train.loc[clean_train["CustomerID"].eq(customer_id) & clean_train["InvoiceFullyIdentified"]]
        row = rfm.loc[rfm["CustomerID"].eq(customer_id)].iloc[0]
        independently_counted_frequency = int(lines["InvoiceNo"].nunique())
        independently_summed_value = int(lines["LineValueMicroGBP"].sum())
        expected_recency = int((cutoff.normalize() - lines["InvoiceTimestamp"].max().normalize()).days)
        assert int(row["Frequency"]) == independently_counted_frequency
        assert int(row["MonetaryMicroGBP"]) == independently_summed_value
        assert int(row["Recency"]) == expected_recency
        checks.append({"CustomerID": customer_id, "Recency": expected_recency, "Frequency": independently_counted_frequency, "MonetaryGBP": independently_summed_value / policy["money_scale"], "status": "reconciled_from_purchase_lines"})
    pd.DataFrame(checks).to_csv(tables / "rfm_spot_checks.csv", index=False)
    examples = baskets.sort_values(["UniqueProducts", "InvoiceNo"]).head(3)["InvoiceNo"].tolist()
    repeated = clean.groupby(["InvoiceNo", "StockCode"]).size()
    if (repeated > 1).any():
        examples.append(repeated[repeated > 1].index[0][0])
    write_csv(items.loc[items["InvoiceNo"].isin(examples)], tables / "basket_spot_checks.csv")
    matches = return_evidence(raw, clean, tables)
    summary.update({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "raw_sha256": raw_hash,
        "cleaning_policy_sha256": sha256(policy_path), "source_code_sha256": sha256(ROOT / "src/preprocessing.py"),
        "basket_item_pairs": len(items), "train_product_vocabulary": len(catalog), "rfm_train_customers": len(rfm),
        "rfm_reference_date": policy["rfm_reference_date"], "cohorts": cohorts,
        "train_rfm_purchase_value_gbp": float(rfm["MonetaryMicroGBP"].sum() / policy["money_scale"]),
        "extreme_purchase_lines_with_later_exact_return_evidence": matches,
        "matrix_shapes": {split: [value["rows"], value["columns"]] for split, value in matrices.items()},
        "checks": {"raw_row_accounting": True, "basket_value_reconciliation": True, "rfm_value_reconciliation": True,
                   "binary_invoice_product_uniqueness": True, "one_split_per_invoice": True, "all_train_source_lines_before_cutoff": True,
                   "train_only_product_catalog_and_transform": True, "sample_rfm_reconciliations": len(checks)},
    })
    verify_raw_unchanged(ROOT, raw_hash)
    (tables / "preparation_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    artifacts = [path for path in data_dir.iterdir() if path.is_file() and path.name not in {".gitkeep", "prepared_manifest.json"}]
    manifest = {"raw_sha256": raw_hash, "policy_sha256": sha256(policy_path), "files": [{"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)} for path in sorted(artifacts)]}
    (data_dir / "prepared_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
