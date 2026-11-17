# Cleaning and feature-preparation policy — version 1.0

This policy was selected after inspecting actual data. Machine-readable settings are in configs/cleaning_policy.json. Decisions state analytical assumptions; separated records are not all asserted to be data-entry errors. This document describes the preparation stage; later models/results are reported separately.

## 1. Investigation evidence

- All 43 invoices with multiple timestamps differ by at most one minute and stay within the same date. No invoice has multiple nonmissing CustomerIDs, multiple countries, or partially missing CustomerID.
- There are 33 StockCodes outside the five-digit-plus-optional-letter pattern. Some are fees/adjustments; others are real products such as gift bags and dog collars. Code shape alone is insufficient for removal.
- Among positive purchase rows before other filters, Description is never missing. There are 5,226 exact repeats after the first occurrence, representing GBP 24,573.74 before merchandise filters.
- There are 1,336 negative-Quantity rows without a C/c invoice prefix; many have zero price or missing descriptions. A negative value is not automatically a verified refund.

Evidence is in results/tables/anomaly_*.csv and anomaly_investigation.json. These observed values are not replaced with synthetic statistics.

## 2. Decisions by data group

| Group | Decision | Rationale and limitations |
|---|---|---|
| Missing/invalid invoice, product, date, or nonnumeric Quantity/UnitPrice | Exclude from purchases; retain reason and SourceRow | Never invent keys or amounts |
| Exact duplicates across all eight raw columns | Keep the first occurrence | A common deduplication assumption; no line ID proves every repeat erroneous. Raw/ledgers support sensitivity analysis |
| Same invoice/product with different valid quantities, prices, times, or other fields | Retain valid lines and sum quantities/values | Distinguish valid repeated lines from exact duplicates; basket presence remains binary |
| C/c invoice or Quantity <= 0 | Exclude from positive purchases; retain ledger | Preserve return/adjustment evidence |
| UnitPrice <= 0 | Exclude from positive-value purchases; retain ledger | Do not reinterpret as ordinary free purchases without context |
| Postage, carriage, platform/bank fees, commission, discount | Separate from merchandise | Avoid product-plus-fee rules and fee inflation of merchandise Monetary |
| M/m = Manual; B = Adjust bad debt | Separate from merchandise | Product cannot be identified, or the row is an accounting entry |
| gift_... codes | Separate vouchers | Stored value is outside the physical-merchandise scope |
| S = Samples; PADS at GBP 0.001 | Separate samples/nominal auxiliary items | Scope decision, not a general low-price filter |
| Reviewed DCGS codes with positive purchases | Retain on an explicit whitelist | Do not discard real products for unusual code structure |
| Unreviewed nonstandard codes | Quarantine; stop if positive unapproved codes remain | Never classify unfamiliar codes automatically as fees/errors |
| Missing CustomerID | Retain for global baskets; exclude from RFM | Never invent IDs. An invoice with partially missing IDs is wholly ineligible for RFM |

Sample tables and counts are retained for review.

## 3. Scope and time boundaries

Retain every country. Report identified cohorts separately; missing-ID customers do not represent a known segment.

| Period | Start, inclusive | End, exclusive |
|---|---|---|
| Train/discovery | 2010-12-01 00:00 | 2011-08-01 00:00 |
| Validation | 2011-08-01 00:00 | 2011-10-01 00:00 |
| Test | 2011-10-01 00:00 | 2011-12-10 00:00 |

Month boundaries make interpretation simple and provide sufficient RFM history; they are not an exact 60/20/20 split. Boundaries were chosen before model fitting, not by performance. Quality auditing covered the full period, so test was not unseen in every possible sense; model performance was reserved for the frozen final evaluation.

## 4. Monetary and returns

Monetary is valid merchandise purchase value **before returns**, not net revenue or profit. Do not delete a past purchase using future return information. Large purchases can later be reversed; segments must describe gross purchasing rather than profitability. Investigation matches are not training features.

## 5. Baskets

- One basket is an InvoiceNo retaining at least one valid merchandise purchase line. Fee-only invoices do not become empty baskets.
- One InvoiceNo–StockCode pair appears once in basket_items, with Present=1. Quantities and values are summed for reconciliation, not counted as repeated association-rule occurrences.
- Single-item baskets remain in the support denominator. Preparation retains rare products; mining may safely prune singletons below the relevant training support threshold without changing the basket denominator.
- Vocabulary/display names use train only. Choose the Description appearing in the most distinct training invoices; break ties alphabetically; use StockCode if no name exists.
- Validation/test long tables retain new products. Train-vocabulary matrices have no new-product columns but keep all row mappings, including rows with no known items; report omitted pairs and zero-known rows.

## 6. RFM and transformation

Use only fully identified training invoices and reference date **2011-08-01 00:00**:

- Recency: calendar days from the last purchase date to the reference date, not rounded-down elapsed hours.
- Frequency: distinct valid purchase invoices, not lines.
- Monetary: valid merchandise purchase value as defined above.

Save original RFM and log1p(R/F/M), then standardize using training-customer mean and population standard deviation (ddof=0). Use scale=1 for a zero-variance feature. Save parameters for reuse. No validation/test customers or transactions may fit transformations, names, or RFM profiles. K selection belongs to the later modeling stage.

## 7. Evidence and reproduction

Run `& .\scripts\run_preparation.ps1` from the project using Python with pandas/numpy/openpyxl; preparation does not need scikit-learn. Derived data go to data/processed and checks to results/tables; raw archive/workbook remain unchanged.

See [data_preparation_report.md](data_preparation_report.md) for measured counts. Mark a TODO complete only after the actual-data pipeline and checks succeed. Preserve the current frozen artifacts; use a separate workspace for a new study run.
