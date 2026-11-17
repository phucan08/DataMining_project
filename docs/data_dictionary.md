# Data dictionary — UCI Online Retail

Source: https://archive.ics.uci.edu/dataset/352/online+retail. The schema was checked against the actual raw workbook: 541,909 rows and the eight columns below. See [raw_audit_report.md](raw_audit_report.md) and results/tables/raw_schema.csv.

| Column | Processing type | Meaning | Checks |
|---|---|---|---|
| InvoiceNo | String identifier | Invoice ID | C/c prefix denotes cancellation; check within-invoice consistency |
| StockCode | String identifier | Product code | Product key; inspect service/adjustment codes |
| Description | Nullable string | Product name | Not a key; one code can have multiple names |
| Quantity | Numeric/integer | Units on one line | Negatives may be returns/adjustments; audit before removing |
| InvoiceDate | Datetime without an assigned time zone | Invoice timestamp | Check parsing, range, and invoice consistency |
| UnitPrice | Numeric | Unit price, GBP | Check nonpositive values and outliers; not profit |
| CustomerID | Nullable string identifier | Customer ID | Never invent IDs; avoid an Excel-derived .0 suffix |
| Country | String | Customer country | Check missingness, distribution, and cohort scope |

## Features built during preparation

| Feature | Definition | Unit/notes |
|---|---|---|
| LineValueMicroGBP | Quantity × UnitPrice, stored in millionths of GBP | After policy 1.0; PurchaseValueGBP is the readable amount |
| Basket | Set of StockCode values in a valid InvoiceNo | Binary presence; Quantity does not duplicate an item |
| Recency | Calendar days from the last purchase to 2011-08-01 | Training history before the cutoff only |
| Frequency | Distinct valid purchase invoices per customer | Not product-line count |
| Monetary | Total valid merchandise purchase value per training customer | Before returns; not net revenue |

Raw statistics are in results/tables/raw_audit.json. CustomerID is missing on 135,080 raw rows and Description on 1,454; other columns have no missing values. Baskets and RFM were built and reconciled; see [data_preparation_report.md](data_preparation_report.md). Display names are learned from train; StockCode remains the key.
