"""Prepare auditable purchase lines, binary baskets and cutoff-safe RFM data."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data_io import COLUMNS


def assign_splits(timestamps: pd.Series, split: dict) -> pd.Series:
    edges = pd.to_datetime([split[key] for key in ["train_start", "train_end_exclusive", "validation_end_exclusive", "test_end_exclusive"]])
    if not all(edges[i] < edges[i + 1] for i in range(3)):
        raise ValueError("Split boundaries must be strictly increasing.")
    if timestamps.isna().any() or ((timestamps < edges[0]) | (timestamps >= edges[3])).any():
        raise ValueError("Invoice timestamp lies outside the configured analysis period.")
    result = pd.Series("test", index=timestamps.index, dtype="string")
    result.loc[timestamps < edges[2]] = "validation"
    result.loc[timestamps < edges[1]] = "train"
    return result


def clean_purchase_lines(raw: pd.DataFrame, policy: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    if list(raw.columns) != COLUMNS:
        raise ValueError("The raw frame must contain exactly the expected original columns.")
    frame = raw.copy()
    frame["SourceRow"] = np.arange(2, len(frame) + 2, dtype=np.int64)
    duplicate = frame.duplicated(subset=COLUMNS, keep="first")
    for column in ["InvoiceNo", "StockCode", "CustomerID", "Country"]:
        frame[column] = frame[column].astype("string")
    frame["InvoiceDate"] = pd.to_datetime(frame["InvoiceDate"], errors="coerce")
    for column in ["Quantity", "UnitPrice"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    invoice_groups = frame.groupby("InvoiceNo", dropna=True)
    metadata = invoice_groups.agg(
        InvoiceTimestamp=("InvoiceDate", "max"), InvoiceFirstTimestamp=("InvoiceDate", "min"),
        KnownCustomerIDs=("CustomerID", "nunique"), Countries=("Country", "nunique"),
        AllLinesHaveCustomerID=("CustomerID", lambda values: bool(values.notna().all())),
    )
    conflict = (metadata["KnownCustomerIDs"] > 1) | (metadata["Countries"] > 1) | (
        metadata["InvoiceFirstTimestamp"].dt.normalize() != metadata["InvoiceTimestamp"].dt.normalize()
    )
    conflict_ids = metadata.index[conflict]
    frame["InvoiceTimestamp"] = frame["InvoiceNo"].map(metadata["InvoiceTimestamp"])
    frame["InvoiceFullyIdentified"] = frame["InvoiceNo"].map(
        metadata["KnownCustomerIDs"].eq(1) & metadata["AllLinesHaveCustomerID"]
    ).fillna(False).astype(bool)

    empty_ids = frame["InvoiceNo"].isna() | frame["StockCode"].isna() | frame["InvoiceNo"].str.strip().eq("") | frame["StockCode"].str.strip().eq("")
    numeric_invalid = ~np.isfinite(frame["Quantity"]) | ~np.isfinite(frame["UnitPrice"]) | (frame["Quantity"].mod(1) != 0)
    invalid = empty_ids.fillna(True) | frame["InvoiceDate"].isna() | numeric_invalid
    cancelled = frame["InvoiceNo"].str.upper().str.startswith("C", na=False)
    code_upper = frame["StockCode"].str.upper()
    excluded_code = code_upper.isin(policy["excluded_stock_codes_case_insensitive"])
    for prefix in policy["excluded_stock_prefixes_case_insensitive"]:
        excluded_code |= code_upper.str.startswith(prefix.upper(), na=False)
    reviewed_merchandise = frame["StockCode"].isin(policy["reviewed_merchandise_stock_codes"])
    standard_merchandise = frame["StockCode"].str.fullmatch(policy["standard_merchandise_pattern"], na=False)
    unreviewed = ~standard_merchandise & ~reviewed_merchandise & ~excluded_code

    reason = pd.Series(pd.NA, index=frame.index, dtype="string")
    cleaning_steps = []
    active = pd.Series(True, index=frame.index)

    def record(stage: str, removal: pd.Series) -> None:
        nonlocal active
        before = frame.loc[active]
        selected = active & removal.fillna(False)
        reason.loc[selected] = stage
        active = active & ~selected
        after = frame.loc[active]
        cleaning_steps.append({
            "stage": stage, "rows_before": len(before), "rows_removed": int(selected.sum()), "rows_after": len(after),
            "invoices_before": int(before["InvoiceNo"].nunique()), "invoices_after": int(after["InvoiceNo"].nunique()),
            "products_before": int(before["StockCode"].nunique()), "products_after": int(after["StockCode"].nunique()),
            "identified_customers_before": int(before["CustomerID"].nunique()), "identified_customers_after": int(after["CustomerID"].nunique()),
        })

    record("invalid_required_fields", invalid)
    record("exact_duplicate", duplicate)
    record("invoice_identity_or_calendar_conflict", frame["InvoiceNo"].isin(conflict_ids))
    record("cancelled_invoice", cancelled)
    record("nonpositive_quantity", frame["Quantity"] <= 0)
    record("nonpositive_unit_price", frame["UnitPrice"] <= 0)
    record("non_merchandise_or_ancillary_code", excluded_code)
    record("unreviewed_stock_code", unreviewed)
    if policy["country_filter"] is not None:
        record("outside_country_cohort", ~frame["Country"].eq(policy["country_filter"]).fillna(False))

    clean = frame.loc[active].copy()
    scaled_price = clean["UnitPrice"] * policy["money_scale"]
    if not np.allclose(scaled_price, np.rint(scaled_price), rtol=0, atol=0.00001):
        raise ValueError("UnitPrice precision exceeds the configured exact-money scale.")
    clean["Quantity"] = clean["Quantity"].astype(np.int64)
    clean["UnitPriceMicroGBP"] = np.rint(scaled_price).astype(np.int64)
    clean["LineValueMicroGBP"] = clean["Quantity"] * clean["UnitPriceMicroGBP"]
    clean["PurchaseValueGBP"] = clean["LineValueMicroGBP"] / policy["money_scale"]
    clean["Split"] = assign_splits(clean["InvoiceTimestamp"], policy["time_split"])
    excluded = frame.loc[~active].copy()
    excluded["FirstExclusionReason"] = reason.loc[~active]
    summary = {
        "raw_rows": len(raw), "clean_purchase_rows": len(clean), "excluded_rows": len(excluded),
        "clean_purchase_invoices": int(clean["InvoiceNo"].nunique()), "clean_product_ids": int(clean["StockCode"].nunique()),
        "clean_known_customer_ids": int(clean["CustomerID"].nunique()), "clean_rows_missing_customer_id": int(clean["CustomerID"].isna().sum()),
        "quarantined_conflicting_invoice_ids": int(conflict.sum()),
        "unreviewed_positive_stock_codes": sorted(frame.loc[unreviewed & ~cancelled & frame["Quantity"].gt(0) & frame["UnitPrice"].gt(0), "StockCode"].dropna().unique().tolist()),
        "purchase_value_micro_gbp": int(clean["LineValueMicroGBP"].sum()),
        "purchase_value_gbp": float(clean["LineValueMicroGBP"].sum() / policy["money_scale"]),
        "money_definition": policy["monetary"], "exact_money_scale": policy["money_scale"],
    }
    if len(clean) + len(excluded) != len(raw):
        raise AssertionError("Cleaning row accounting failed.")
    return clean, excluded, pd.DataFrame(cleaning_steps), summary


def make_baskets(clean: pd.DataFrame, policy: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    invoice = clean.groupby("InvoiceNo", sort=True).agg(
        InvoiceTimestamp=("InvoiceTimestamp", "first"), CustomerID=("CustomerID", "first"), Country=("Country", "first"),
        FullyIdentified=("InvoiceFullyIdentified", "all"), Split=("Split", "first"),
        UniqueProducts=("StockCode", "nunique"), TotalQuantity=("Quantity", "sum"), PurchaseValueMicroGBP=("LineValueMicroGBP", "sum"),
    ).reset_index()
    invoice.loc[~invoice["FullyIdentified"], "CustomerID"] = pd.NA
    invoice["PurchaseValueGBP"] = invoice["PurchaseValueMicroGBP"] / policy["money_scale"]
    invoice["SingleItemBasket"] = invoice["UniqueProducts"].eq(1)
    items = clean.groupby(["InvoiceNo", "StockCode"], sort=True).agg(
        Quantity=("Quantity", "sum"), PurchaseValueMicroGBP=("LineValueMicroGBP", "sum")
    ).reset_index()
    items["Present"] = np.int8(1)
    items = items.merge(invoice[["InvoiceNo", "Split"]], on="InvoiceNo", how="left", validate="many_to_one")
    items["PurchaseValueGBP"] = items["PurchaseValueMicroGBP"] / policy["money_scale"]
    if items.duplicated(["InvoiceNo", "StockCode"]).any() or items["PurchaseValueMicroGBP"].sum() != invoice["PurchaseValueMicroGBP"].sum():
        raise AssertionError("Basket accounting or binary-key uniqueness failed.")
    return invoice, items


def fit_train_catalog(clean: pd.DataFrame) -> pd.DataFrame:
    train = clean.loc[clean["Split"].eq("train")]
    names = train.loc[train["Description"].notna() & train["Description"].astype("string").str.strip().ne("")].groupby(
        ["StockCode", "Description"], sort=True
    )["InvoiceNo"].nunique().rename("DescriptionInvoiceCount").reset_index()
    names = names.sort_values(["StockCode", "DescriptionInvoiceCount", "Description"], ascending=[True, False, True]).drop_duplicates("StockCode")
    catalog = pd.DataFrame({"StockCode": sorted(train["StockCode"].unique())})
    catalog = catalog.merge(names, on="StockCode", how="left", validate="one_to_one")
    catalog["DisplayName"] = catalog["Description"].fillna(catalog["StockCode"])
    catalog.insert(0, "ColumnIndex", np.arange(len(catalog), dtype=np.int32))
    return catalog.drop(columns="Description")


def make_rfm(baskets: pd.DataFrame, policy: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    cutoff = pd.Timestamp(policy["rfm_reference_date"])
    if cutoff != pd.Timestamp(policy["time_split"]["train_end_exclusive"]):
        raise ValueError("RFM reference date must equal the exclusive train cutoff.")
    eligible = baskets.loc[baskets["Split"].eq("train") & baskets["FullyIdentified"] & baskets["CustomerID"].notna()]
    if eligible.empty:
        raise ValueError("No identified train customers available for RFM.")
    if not eligible["InvoiceTimestamp"].lt(cutoff).all():
        raise AssertionError("RFM includes future invoices.")
    rfm = eligible.groupby("CustomerID", sort=True).agg(
        LastPurchase=("InvoiceTimestamp", "max"), Frequency=("InvoiceNo", "nunique"), MonetaryMicroGBP=("PurchaseValueMicroGBP", "sum")
    ).reset_index()
    rfm["Recency"] = (cutoff.normalize() - rfm["LastPurchase"].dt.normalize()).dt.days
    rfm["Monetary"] = rfm["MonetaryMicroGBP"] / policy["money_scale"]
    rfm = rfm[["CustomerID", "Recency", "Frequency", "Monetary", "MonetaryMicroGBP", "LastPurchase"]]
    values = rfm[["Recency", "Frequency", "Monetary"]].astype(float)
    if (values < 0).any().any():
        raise AssertionError("RFM values must be nonnegative.")
    logged = np.log1p(values)
    means = logged.mean()
    deviations = logged.std(ddof=0).replace(0, 1.0)
    normalized = (logged - means) / deviations
    features = normalized.rename(columns={name: name + "LogZ" for name in values.columns})
    features.insert(0, "CustomerID", rfm["CustomerID"].to_numpy())
    parameters = {
        "fit_split": "train", "reference_date_exclusive": cutoff.isoformat(), "fit_customers": len(rfm),
        "input_columns": list(values.columns), "transformation": "log1p_then_population_standardization",
        "log_means": means.to_dict(), "log_population_scales": deviations.to_dict(),
        "raw_train_skewness": {name: (None if pd.isna(value) else float(value)) for name, value in values.skew().items()},
        "zero_variance_scale_policy": "use_1", "monetary_definition": policy["monetary"],
    }
    if not np.isfinite(features.drop(columns="CustomerID").to_numpy()).all():
        raise AssertionError("RFM standardized features contain nonfinite values.")
    return rfm, features, parameters


def save_sparse_baskets(baskets: pd.DataFrame, items: pd.DataFrame, catalog: pd.DataFrame, output: Path) -> dict:
    columns = catalog.set_index("StockCode")["ColumnIndex"]
    matrices = {}
    for split in ["train", "validation", "test"]:
        row_map = baskets.loc[baskets["Split"].eq(split), ["InvoiceNo"]].sort_values("InvoiceNo").reset_index(drop=True)
        row_map.insert(0, "RowIndex", np.arange(len(row_map), dtype=np.int32))
        row_map.to_csv(output / f"basket_{split}_row_index.csv", index=False)
        selected = items.loc[items["Split"].eq(split)].copy()
        selected["ColumnIndex"] = selected["StockCode"].map(columns)
        known = selected.loc[selected["ColumnIndex"].notna()].merge(row_map, on="InvoiceNo", validate="many_to_one")
        shape = (len(row_map), len(catalog))
        np.savez_compressed(
            output / f"basket_{split}_coordinates.npz", row_indices=known["RowIndex"].to_numpy(dtype=np.int32),
            column_indices=known["ColumnIndex"].to_numpy(dtype=np.int32), values=np.ones(len(known), dtype=np.int8),
            shape=np.array(shape, dtype=np.int64),
        )
        matrices[split] = {
            "format": "project_coo_numpy_v1_not_scipy_save_npz", "rows": shape[0], "columns": shape[1],
            "nonzero_entries": len(known), "unknown_train_product_pairs": int(selected["ColumnIndex"].isna().sum()),
            "unknown_train_product_ids": int(selected.loc[selected["ColumnIndex"].isna(), "StockCode"].nunique()),
            "rows_with_no_known_train_product": len(row_map) - int(known["RowIndex"].nunique()),
            "dense_boolean_bytes_estimate": int(shape[0] * shape[1]),
        }
    (output / "basket_matrix_metadata.json").write_text(json.dumps(matrices, indent=2) + "\n", encoding="utf-8")
    return matrices
