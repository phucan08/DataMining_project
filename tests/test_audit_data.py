"""Check audit counts on a controlled frame; the full workbook is audited separately."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.audit_data import EXPECTED_COLUMNS, audit, file_sha256


class AuditTests(unittest.TestCase):
    def frame(self):
        rows = [
            ["1", "A", "Item A", 2, "2011-01-01", 1.5, "10", "UK"],
            ["1", "A", "Item A", 2, "2011-01-01", 1.5, "10", "UK"],
            ["C2", "A", None, -1, "2011-02-01", 1.5, None, "UK"],
            ["3", "B", "Item B", 0, "bad date", 0, "20", "FR"],
            ["3", "B", "Item B renamed", 1, "2011-02-03", -2, "21", "FR"],
        ]
        return pd.DataFrame(rows, columns=EXPECTED_COLUMNS)

    def test_counts_overlap_without_deleting_or_overwriting_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.xlsx"
            raw.write_bytes(b"test placeholder; read_excel is mocked")
            original_hash = file_sha256(raw)
            with patch("pandas.read_excel", return_value=self.frame()):
                result = audit(raw, root / "output")
            self.assertEqual(result["rows"], 5)
            self.assertEqual(result["distinct_invoice_ids"], 3)
            self.assertEqual(result["exact_duplicate_rows_after_first"], 1)
            self.assertEqual(result["repeated_invoice_product_rows_after_first"], 2)
            self.assertEqual(result["cancelled_invoice_rows"], 1)
            self.assertEqual(result["quantity_negative_rows"], 1)
            self.assertEqual(result["unit_price_negative_rows"], 1)
            self.assertEqual(result["invalid_nonmissing_dates"], 1)
            self.assertEqual(result["invoice_ids_with_multiple_nonmissing_customers"], 1)
            self.assertEqual(result["missing_by_column"]["CustomerID"], 1)
            self.assertEqual(result["input_sha256"], original_hash)
            self.assertEqual(file_sha256(raw), original_hash)
            self.assertEqual(len(list((root / "output").glob("*"))), 5)

    def test_missing_columns_stop_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.xlsx"
            raw.write_bytes(b"test")
            with patch("pandas.read_excel", return_value=self.frame().drop(columns=["StockCode"])):
                with self.assertRaisesRegex(ValueError, "Missing expected columns"):
                    audit(raw, root / "output")
            self.assertFalse((root / "output").exists())

    def test_empty_workbook_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.xlsx"
            raw.write_bytes(b"test")
            with patch("pandas.read_excel", return_value=self.frame().iloc[:0]):
                with self.assertRaisesRegex(ValueError, "no transaction rows"):
                    audit(raw, root / "output")
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
