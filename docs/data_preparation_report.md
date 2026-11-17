# Cleaning, basket, and RFM preparation report

The pipeline ran on the actual workbook; raw-hash checks and reconciliation passed. Statistics timestamp (UTC): 2026-11-17T17:06:55.789210+00:00. This records preparation, before the separately documented model experiments.

## 1. Main results

| Metric | Value |
|---|---:|
| Raw rows | 541,909 |
| Valid merchandise purchase lines under the policy | 522,537 |
| Lines separated from purchases, retained in ledger/raw | 19,372 |
| Full-period baskets | 19,773 |
| Full-period merchandise codes | 3,907 |
| Nonmissing cleaned full-period CustomerIDs | 4,334 |
| Missing-ID purchase lines retained for baskets | 131,387 |
| Full-period binary invoice/product pairs | 517,289 |
| Training customers with RFM profiles | 3,145 |
| Training product vocabulary | 3,564 |

The difference between full-period customers and RFM is due to the train-only, identified-customer scope, not use of validation/test information. Apriori/FP-Growth/K-means belong to the later stage.

## 2. Ordered cleaning log

| Step | Rows before | Rows separated here | Rows after | Invoices after | Identified customers after |
|---|---:|---:|---:|---:|---:|
| Missing/invalid mandatory fields | 541,909 | 0 | 541,909 | 25,900 | 4,372 |
| Exact duplicates across eight raw columns | 541,909 | 5,268 | 536,641 | 25,900 | 4,372 |
| Conflicting invoice ID/country/date | 536,641 | 0 | 536,641 | 25,900 | 4,372 |
| C/c invoices | 536,641 | 9,251 | 527,390 | 22,064 | 4,339 |
| Remaining nonpositive Quantity | 527,390 | 1,336 | 526,054 | 20,728 | 4,339 |
| Remaining nonpositive UnitPrice | 526,054 | 1,176 | 524,878 | 19,960 | 4,338 |
| Fees/vouchers/manual/samples/auxiliary | 524,878 | 2,341 | 522,537 | 19,773 | 4,334 |
| Unapproved merchandise codes | 522,537 | 0 | 522,537 | 19,773 | 4,334 |

Each separated row receives its first exclusion reason, so this column can be summed. Raw issue counts can overlap and cannot be summed directly. Decisions/assumptions are in [data_preparation_policy.md](data_preparation_policy.md).

## 3. Anomalies and decisions

- The 43 multi-timestamp invoices differ by at most one minute and never cross a date. Use the last timestamp and keep each invoice together.
- Review all 33 nonstandard codes. Retain seven approved DCGS merchandise codes; separate fees/vouchers/samples/accounting entries. No unapproved positive-purchase codes remain.
- Keep the first exact duplicate as an explicit assumption; raw/excluded_lines preserve evidence. Other valid repeated-product lines retain summed quantities/values.
- Never invent CustomerIDs. Retain all countries and large transactions without percentile trimming. Keep single-item baskets in support denominators.

### Returns and the Monetary limitation

Monetary is merchandise purchases before returns, not net revenue/profit. Among the ten largest purchase-Quantity lines, the following later quantity-reversal counterparts were found. This is a sample check, not a complete return-matching system.

| Purchase invoice | Counterpart invoice | Product | Purchase Quantity | Minutes later | Purchase GBP |
|---|---|---|---:|---:|---:|
| 581483 | C581484 | 23843 | 80,995 | 12 | 168,469.60 |
| 541431 | C541433 | 23166 | 74,215 | 16 | 77,183.60 |
| 540815 | C550456 | 21108 | 3,114 | 139,693 | 6,539.40 |

Future returns never erase past training purchases. Gross purchasers may have high Monetary despite subsequent returns; segment names must not assume profitability or absence of returns. Counterpart matches are investigative evidence, not training features.

## 4. Time splits and cohorts

- Train: [2010-12-01T00:00:00, 2011-08-01T00:00:00).
- Validation: [2011-08-01T00:00:00, 2011-10-01T00:00:00).
- Test: [2011-10-01T00:00:00, 2011-12-10T00:00:00).

| Split | Purchase lines | Baskets | Identified customers | Single-item baskets | Customer IDs new to train |
|---|---:|---:|---:|---:|---:|
| train | 274,949 | 11,044 | 3,145 | 898 | 0 |
| validation | 82,802 | 3,157 | 1,769 | 213 | 468 |
| test | 164,786 | 5,572 | 2,559 | 389 | 929 |

Every training source line precedes the cutoff. Full-period quality inspection did not choose parameters from test-model outcomes. Only customers with training profiles receive frozen historical segments later; new/missing-ID customers require separate reporting/fallback.

## 5. Basket matrices and new products

| Split | Rows | Training columns | Nonzero entries | Pairs outside vocabulary | Baskets with no training item |
|---|---:|---:|---:|---:|---:|
| train | 11,044 | 3,564 | 272,890 | 0 | 0 |
| validation | 3,157 | 3,564 | 77,821 | 4,345 | 26 |
| test | 5,572 | 3,564 | 141,570 | 20,663 | 143 |

The basket_items long table retains every product. Matrices use the training vocabulary and keep every basket row, including zero-known-item rows. Coordinate NPZ is the project's own format, not scipy.sparse.save_npz.

## 6. Training RFM and transformations

Exclusive reference date = 2011-08-01T00:00:00. Reconciled Monetary from identified training invoices = GBP 4,511,871.99.

Frequency counts distinct invoices; Recency counts calendar days; Monetary sums valid merchandise purchases. Examples were checked directly against purchase_lines:

| CustomerID | Recency, days | Frequency, invoices | Monetary GBP |
|---|---:|---:|---:|
| 12346 | 195 | 1 | 77,183.60 |
| 12347 | 53 | 4 | 2,205.95 |
| 12348 | 118 | 3 | 1,167.24 |
| 14646 | 12 | 33 | 135,455.13 |
| 18102 | 4 | 25 | 129,551.31 |

| Variable | Original train skewness | Mean after log1p | Population scale after log1p |
|---|---:|---:|---:|
| Recency | 0.8140 | 3.945981 | 1.123532 |
| Frequency | 9.0179 | 1.191140 | 0.594879 |
| Monetary | 15.3491 | 6.340940 | 1.186446 |

Original RFM and log1p/standardized features (ddof=0) are saved. Parameters fit training customers only. This preparation configuration was not itself proof of optimal clustering, and K was not selected during this step.

## 7. Outputs

| File under data/processed | Meaning |
|---|---|
| purchase_lines.csv.gz | Valid purchases with SourceRow, source/invoice timestamps, split, exact money |
| excluded_lines.csv.gz | Separated lines and FirstExclusionReason |
| returns_adjustments_raw.csv.gz | Raw cancellation/nonpositive-Quantity/price ledger; overlaps exclusions, so do not add the tables |
| baskets.csv | One invoice row with ID cohort/profile eligibility |
| basket_items.csv.gz | One InvoiceNo–StockCode row, Present=1, including new products |
| product_catalog_train.csv | ColumnIndex and train-only display names |
| basket_*_coordinates.npz | row_indices, column_indices, values, shape per split |
| basket_*_row_index.csv | RowIndex–InvoiceNo mapping per split |
| basket_matrix_metadata.json | Shapes, nonzeros, new products, zero-known rows |
| rfm_train.csv | CustomerID, original R/F/M, integer money, LastPurchase |
| rfm_train_features.csv | CustomerID, RecencyLogZ, FrequencyLogZ, MonetaryLogZ |
| rfm_transform.json | Cutoff, transformation parameters, training statistics |
| prepared_manifest.json | Derived-data SHA-256 and raw/policy hash links |

Evidence under results/tables includes cleaning_log.csv, prepared_cohort_summary.csv, preparation_summary.json, rfm_train_summary.csv, spot checks, and investigation tables.

## 8. Verification and reproduction

Reconciled raw = clean + excluded; item-pair count = summed UniqueProducts; line value = basket value; RFM money = eligible identified training-invoice money. Every invoice has one split, all training source timestamps precede cutoff, and raw SHA-256 is unchanged.

Run `& .\scripts\run_preparation.ps1` in a separate reproduction workspace to preserve current frozen artifacts. Tests cover cutoff boundaries, missing IDs, future products, repeated lines, conflicting invoices, and effects of future purchases/returns. Preparation needs pandas/numpy/openpyxl; modeling uses the separately documented Weka environment.
