# Raw audit report — UCI Online Retail

This is the raw-audit stage record. The actual workbook was read and measured without deleting rows, imputing values, constructing baskets, or fitting models in this step. Later stages are documented separately.

## 1. Source and integrity

- Source: https://archive.ics.uci.edu/dataset/352/online+retail.
- Original download: https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip.
- ZIP obtained from the UCI Download button, copied to data/raw after completion, and checked for ZIP CRC integrity.
- Source metadata timestamp (UTC): 2026-11-17T08:03:45.859092+00:00.
- License: CC BY 4.0. Original archive/workbook retained with SHA-256.

| File | Bytes | SHA-256 |
|---|---:|---|
| online_retail.zip | 23,715,478 | `f5385cbb54bbebf7196389109c6b0621faab0c304e3702548165e71c84aede8b` |
| Online Retail.xlsx | 23,715,344 | `43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d` |

The workbook hash was checked again after statistics were calculated to detect modification during the audit.

## 2. Measured overview

| Metric | Result |
|---|---:|
| Product transaction lines | 541,909 |
| Columns | 8 |
| Distinct invoice IDs, including cancellations | 25,900 |
| Distinct product codes, including service codes | 4,070 |
| Distinct nonmissing CustomerIDs | 4,372 |
| Countries | 38 |
| First timestamp | 2010-12-01T08:26:00 |
| Last timestamp | 2011-12-09T12:50:00 |

One row is a product line, not a basket. Raw totals are not counts of completed valid purchases. Prices are GBP; no timestamp time zone was inferred.

## 3. Schema and missing values

| Column | Loaded type | Missing | Missing rate | Distinct nonmissing |
|---|---|---:|---:|---:|
| InvoiceNo | string | 0 | 0.00% | 25,900 |
| StockCode | string | 0 | 0.00% | 4,070 |
| Description | object | 1,454 | 0.27% | 4,223 |
| Quantity | int64 | 0 | 0.00% | 722 |
| InvoiceDate | datetime64[us] | 0 | 0.00% | 23,260 |
| UnitPrice | float64 | 0 | 0.00% | 1,630 |
| CustomerID | string | 135,080 | 24.93% | 4,372 |
| Country | str | 0 | 0.00% | 38 |

CustomerID is a nullable string identifier, never an invented customer. Missing-ID rows must be excluded from RFM; their eligibility for global baskets depends on invoice cleaning. Description is not a product key.

## 4. Data-quality issues

| Check | Count | Unit |
|---|---:|---|
| Exact duplicates after first occurrence | 5,268 | rows |
| Repeated InvoiceNo–StockCode pairs after first occurrence | 10,684 | rows |
| StockCodes with multiple nonmissing Descriptions | 650 | product codes |
| InvoiceNo starts with C/c | 9,288 | rows |
| Negative Quantity | 10,624 | rows |
| Zero Quantity | 0 | rows |
| Negative UnitPrice | 2 | rows |
| Zero UnitPrice | 2,515 | rows |
| Nonmissing dates that fail parsing | 0 | rows |
| Nonmissing nonnumeric Quantity | 0 | rows |
| Nonmissing nonnumeric UnitPrice | 0 | rows |
| InvoiceNo with multiple nonmissing CustomerIDs | 0 | invoice IDs |
| InvoiceNo with multiple timestamps | 43 | invoice IDs |

Issue groups overlap and must not be added to estimate exclusions. Repeated invoice/product pairs are not automatically erroneous: binary baskets record presence, while monetary aggregation needs a separate deduplication policy.

The 43 multi-timestamp invoices require review and a representative invoice-time rule before splitting; never split their lines across periods.

## 5. Time and country scope

| Month | Raw rows | Invoice IDs appearing in month |
|---|---:|---:|
| 2010-12 | 42,481 | 2,025 |
| 2011-01 | 35,147 | 1,476 |
| 2011-02 | 27,707 | 1,393 |
| 2011-03 | 36,748 | 1,983 |
| 2011-04 | 29,916 | 1,744 |
| 2011-05 | 37,030 | 2,162 |
| 2011-06 | 36,874 | 2,012 |
| 2011-07 | 39,518 | 1,927 |
| 2011-08 | 35,284 | 1,737 |
| 2011-09 | 50,226 | 2,327 |
| 2011-10 | 60,742 | 2,637 |
| 2011-11 | 84,711 | 3,462 |
| 2011-12 | 25,525 | 1,015 |

December 2011 ends on December 9; do not compare it directly with complete months. These are IDs appearing within each month, before standardized assignment by a representative invoice timestamp.

| Countries with most raw rows | Raw rows | Row share |
|---|---:|---:|
| United Kingdom | 495,478 | 91.43% |
| Germany | 9,495 | 1.75% |
| France | 8,557 | 1.58% |
| EIRE | 8,196 | 1.51% |
| Spain | 2,533 | 0.47% |

The complete table is results/tables/raw_country_counts.csv. No country filter was fixed at this audit stage; all raw countries were retained.

## 6. Values and outliers requiring investigation

| Raw variable | Min | Median | P99 | Max |
|---|---:|---:|---:|---:|
| Quantity | -80,995.00 | 3.00 | 100.00 | 80,995.00 |
| UnitPrice | -11,062.06 | 2.08 | 18.00 | 38,970.00 |
| RawLineValue | -168,469.60 | 9.75 | 180.00 | 168,469.60 |

RawLineValue = Quantity × UnitPrice on raw data, including cancellations/returns/adjustments. It is not yet Monetary or revenue. Large values may reflect wholesale purchases and require investigation before rejection or percentile trimming.

## 7. Follow-up proposed at the audit stage

1. Inspect cancellations/returns, nonpositive prices, fee/service codes, and repeats; adopt an evidence-based policy.
2. Separate valid purchases for baskets from identified customers for RFM; report each exclusion step.
3. Review multiple invoice timestamps and inconsistent names before fixing invoice times/display names.
4. Select country scope and time boundaries; fit transformations/models only on discovery/train.
5. Do not predetermine clean-row counts, clusters, or rules.

These subsequent tasks were later completed as recorded in [data_preparation_report.md](data_preparation_report.md) and later experiment reports.

## 8. Reproduction and evidence

Run `& .\scripts\run_raw_audit.ps1` from the project. The runner chooses Python with pandas/numpy/openpyxl, checks raw SHA-256, records the environment, and rebuilds audit tables. English report snapshots are retained once final artifacts are frozen.

Audit environment: Python 3.12.14; pandas 3.0.1; numpy 2.3.5; openpyxl 3.1.5. At the original audit milestone, scikit-learn/mlxtend/plotting libraries were unavailable; that milestone did not claim modeling readiness. The later workflow uses Weka and ReportLab/Sharp.

Evidence: raw_audit.json, raw_schema.csv, raw_monthly_counts.csv, raw_country_counts.csv, raw_numeric_summary.csv under results/tables. This step changed or removed no raw rows.
