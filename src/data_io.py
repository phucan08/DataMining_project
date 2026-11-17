"""Read verified raw input and keep identifiers separate from numeric values."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

COLUMNS = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_verified_raw(root: Path) -> tuple[pd.DataFrame, str]:
    raw_path = root / "data/raw/Online Retail.xlsx"
    metadata = json.loads((root / "data/raw/source_metadata.json").read_text(encoding="utf-8"))
    expected = next(record["sha256"] for record in metadata["files"] if record["name"] == raw_path.name)
    actual = sha256(raw_path)
    if actual != expected:
        raise RuntimeError("Raw workbook hash differs from source metadata.")
    frame = pd.read_excel(raw_path, engine="openpyxl", dtype={"InvoiceNo": "string", "StockCode": "string", "CustomerID": "string"})
    if list(frame.columns) != COLUMNS:
        raise ValueError(f"Unexpected raw schema: {list(frame.columns)}")
    return frame, actual


def verify_raw_unchanged(root: Path, expected_hash: str) -> None:
    if sha256(root / "data/raw/Online Retail.xlsx") != expected_hash:
        raise RuntimeError("Raw workbook changed while processing.")
