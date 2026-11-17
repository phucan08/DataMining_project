"""Test temporal boundaries, cohort handling, exact money and binary baskets."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_io import COLUMNS
from src.preprocessing import clean_purchase_lines, fit_train_catalog, make_baskets, make_rfm, save_sparse_baskets

ROOT = Path(__file__).resolve().parents[1]


def row(invoice, code="10001", description="Item A", quantity=1, date="2011-07-01", price=10, customer="10", country="United Kingdom"):
    return [invoice, code, description, quantity, pd.Timestamp(date), price, customer, country]


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / "configs/cleaning_policy.json").read_text())

    def frame(self):
        original = row("1", quantity=2)
        rows = [
            original, original.copy(), row("1", quantity=3), row("1", "DCGSSBOY", "BOYS PARTY BAG", price=2),
            row("1", "POST", "POSTAGE", price=5),
            row("2", "10002", "Item B", date="2011-07-31", price=4, customer=None),
            row("3", "10002", "Item B", date="2011-07-20", price=4, customer="20"),
            row("4", "10003", "Future product", date="2011-08-01", price=9999),
            row("5", date="2011-10-01", customer="30"),
            row("C6", quantity=-2, date="2011-07-15"),
            row("7", quantity=np.nan),
        ]
        return pd.DataFrame(rows, columns=COLUMNS)

    def test_cleaning_accounting_retains_reviewed_goods_and_guest_baskets(self):
        raw = self.frame()
        original = raw.copy(deep=True)
        clean, excluded, log, summary = clean_purchase_lines(raw, self.policy)
        pd.testing.assert_frame_equal(raw, original)
        self.assertEqual(len(clean), 7)
        self.assertEqual(len(clean) + len(excluded), len(raw))
        self.assertEqual(int(log["rows_removed"].sum()), len(excluded))
        self.assertIn("DCGSSBOY", set(clean["StockCode"]))
        self.assertNotIn("POST", set(clean["StockCode"]))
        self.assertEqual(summary["clean_rows_missing_customer_id"], 1)
        self.assertEqual(set(excluded["FirstExclusionReason"]), {"exact_duplicate", "cancelled_invoice", "invalid_required_fields", "non_merchandise_or_ancillary_code"})

    def test_binary_item_pairs_and_rfm_money_are_not_line_counts(self):
        clean, _, _, _ = clean_purchase_lines(self.frame(), self.policy)
        baskets, items = make_baskets(clean, self.policy)
        rfm, features, params = make_rfm(baskets, self.policy)
        item = items.loc[items["InvoiceNo"].eq("1") & items["StockCode"].eq("10001")].iloc[0]
        self.assertEqual(item["Quantity"], 5)
        self.assertEqual(item["Present"], 1)
        self.assertEqual(item["PurchaseValueMicroGBP"], 50_000_000)
        customer = rfm.loc[rfm["CustomerID"].eq("10")].iloc[0]
        self.assertEqual(customer["Frequency"], 1)
        self.assertEqual(customer["MonetaryMicroGBP"], 52_000_000)
        self.assertEqual(customer["Recency"], 31)
        self.assertEqual(set(rfm["CustomerID"]), {"10", "20"})
        self.assertTrue(np.isfinite(features.drop(columns="CustomerID")).all().all())
        self.assertEqual(params["fit_split"], "train")

    def test_invoice_at_intraday_cutoff_uses_last_line_and_cannot_enter_train(self):
        policy = copy.deepcopy(self.policy)
        policy["time_split"]["train_end_exclusive"] = "2011-08-01T12:00:00"
        policy["rfm_reference_date"] = "2011-08-01T12:00:00"
        raw = pd.DataFrame([
            row("1", date="2011-08-01 11:59:00"),
            row("1", "10002", "Item B", date="2011-08-01 12:00:00"),
            row("2", date="2011-07-01"),
        ], columns=COLUMNS)
        clean, _, _, _ = clean_purchase_lines(raw, policy)
        self.assertEqual(set(clean.loc[clean["InvoiceNo"].eq("1"), "Split"]), {"validation"})
        baskets, _ = make_baskets(clean, policy)
        rfm, _, _ = make_rfm(baskets, policy)
        self.assertEqual(rfm.iloc[0]["Frequency"], 1)

    def test_conflicting_id_and_calendar_day_quarantine_entire_invoice(self):
        raw = pd.DataFrame([
            row("1", customer="10"), row("1", "10002", "B", customer="20"),
            row("2", date="2011-07-31 23:59:00"), row("2", "10002", "B", date="2011-08-01 00:00:00"),
            row("3"),
        ], columns=COLUMNS)
        clean, excluded, _, summary = clean_purchase_lines(raw, self.policy)
        self.assertEqual(set(clean["InvoiceNo"]), {"3"})
        self.assertEqual(summary["quarantined_conflicting_invoice_ids"], 2)
        self.assertTrue(excluded["FirstExclusionReason"].eq("invoice_identity_or_calendar_conflict").all())

    def test_future_sales_labels_and_returns_do_not_change_train_features_or_vocabulary(self):
        raw = self.frame()
        clean, _, _, _ = clean_purchase_lines(raw, self.policy)
        baskets, _ = make_baskets(clean, self.policy)
        catalog = fit_train_catalog(clean)
        rfm, features, params = make_rfm(baskets, self.policy)
        extra = pd.DataFrame([
            row("F1", description="Future renamed item", date="2011-11-01", price=10**6),
            row("CF1", quantity=-2, date="2011-12-01"),
        ], columns=COLUMNS)
        extended, _, _, _ = clean_purchase_lines(pd.concat([raw, extra], ignore_index=True), self.policy)
        future_baskets, _ = make_baskets(extended, self.policy)
        after_rfm, after_features, after_params = make_rfm(future_baskets, self.policy)
        pd.testing.assert_frame_equal(rfm, after_rfm)
        pd.testing.assert_frame_equal(features, after_features)
        pd.testing.assert_frame_equal(catalog, fit_train_catalog(extended))
        self.assertEqual(params, after_params)
        self.assertNotIn("10003", set(catalog["StockCode"]))

    def test_unknown_future_products_preserve_empty_matrix_rows(self):
        clean, _, _, _ = clean_purchase_lines(self.frame(), self.policy)
        baskets, items = make_baskets(clean, self.policy)
        catalog = fit_train_catalog(clean)
        with tempfile.TemporaryDirectory() as directory:
            result = save_sparse_baskets(baskets, items, catalog, Path(directory))
            with np.load(Path(directory) / "basket_validation_coordinates.npz") as matrix:
                self.assertEqual(matrix["shape"].tolist(), [1, 3])
                self.assertEqual(len(matrix["values"]), 0)
            self.assertEqual(result["validation"]["rows_with_no_known_train_product"], 1)
            self.assertEqual(result["validation"]["unknown_train_product_pairs"], 1)

    def test_partial_missing_customer_is_not_filled_or_used_for_rfm(self):
        raw = pd.DataFrame([
            row("1", customer="10"), row("1", "10002", "B", customer=None), row("2", customer="20"),
        ], columns=COLUMNS)
        clean, _, _, _ = clean_purchase_lines(raw, self.policy)
        baskets, _ = make_baskets(clean, self.policy)
        self.assertEqual(clean["CustomerID"].isna().sum(), 1)
        self.assertTrue(pd.isna(baskets.loc[baskets["InvoiceNo"].eq("1"), "CustomerID"].iloc[0]))
        rfm, _, _ = make_rfm(baskets, self.policy)
        self.assertEqual(set(rfm["CustomerID"]), {"20"})


if __name__ == "__main__":
    unittest.main()
