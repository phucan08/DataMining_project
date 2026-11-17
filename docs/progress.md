# Progress log — updated 2026-11-18

Milestones below are historical snapshots. A limitation at an earlier milestone does not describe the latest completed stage.

## Latest milestone — final test and consolidated report

- Freeze SHA-256 for data, 738 global rules, cohort/segment rules, models/scaler, and evaluator before scoring. No refitting or test-based threshold/K changes. Additional protocol recorded before scoring.
- Test: 5,572 baskets, 5,183 eligible for one-item masking, 389 single-item baskets; 743 unseen targets remain in the denominator.
- All-test global: 458/5,183 = 8.84%; popularity: 90/5,183 = 1.74%. Difference +7.10 percentage points, paired customer bootstrap 95% CI [+6.34; +7.89].
- Same 3,579 training-profile baskets: segment 317 hits = 8.86%, identified-global 315 = 8.80%. Difference +0.056 percentage points, CI [−0.475; +0.600]. Insufficient evidence of segment improvement.
- Paired bootstrap: 2,000 CustomerID resamples; missing-ID invoices are individual units. Save Precision@5, coverage, fallback, new/missing-ID customer and segment breakdowns, rule stability, errors.
- Repeat calls return verified saved results, without rescoring. Lock/receipt confirm raw/prepared/model integrity. All 24 tests pass; training runner stops when final lock exists.
- Figure 16 adds test confidence intervals; 16 PNG/SVG pairs overall. [Final report](final_evaluation_report.md), [consolidated research report](../report/project_report.md), README/TODO updated: 117 completed tasks, 44 pending.
- Historical train/validation test=false flags are retained; current state is configs/project.json and results/tables/final_test/evaluation_receipt.json.

**Next:** check rubric when available, format the report, prepare slides/defense, validate the submission package. No submission or instructor/team/deadline confirmation yet. Do not select models using the already-used test.

## Documentation and workspace cleanup

- Translate all retained project Markdown documents into English, preserving findings, links, and checklist states.
- Remove the obsolete duplicate checklist; TODO.md is the single active checklist.
- Remove pip-only failed local environments, disposable compiled Java output, Python caches, abandoned empty benchmark output, and task-specific temporary files.
- Preserve raw/processed data, source/tests, selected and diagnostic models, provenance manifests, benchmark inputs/tables/logs, and figures.
- Retain the edited English report snapshots after the final freeze, preventing report scripts from overwriting them with earlier text.

## Before final test — EDA and training/validation experiments

- Create 15 SVG/PNG figures and source tables: time, basket size/value, products, countries, RFM, purchase concentration, correlation, K selection, PCA, profiles, experiments.
- Use Weka 3.8.7/Java for algorithms, Python/pandas/NumPy for checks/metrics, ReportLab/Sharp for charts; record versions/jar hashes without claiming sklearn/mlxtend installation.
- Full-train FP-Growth completes 1%/2%/5% support. Apriori times out at 45 seconds for 1%/2%, completes 5%. Same 500-training-invoice subset at 2%/5%, three repetitions, yields identical rules/counts. Timings combine fitting/rule generation; no separate mining/memory measurements.
- Select among 18 configurations: support 1%, confidence 0.3, lift≥1.1, two total rule items, 738 rules. Validation 405/2,944 = 13.76%; popularity 82/2,944 = 2.79%. These are selection results.
- K-means K=2–8, five seed groups ×20 starts/K = 700 initializations. K=2 after full-3,145-customer silhouette, SSE, ARI, size, interpretation; mean silhouette 0.4440, mean ARI 0.9954.
- Segment_1: 1,048 customers, median R=19 days/F=5/M=GBP 1,639.795. Segment_2: 2,097, R=102/F=1/M=GBP 315. Monetary is gross purchases before returns, not churn/profit labels.
- Same 2,274 eligible validation baskets: global 14.51%, segment 14.07%, popularity 2.81%. No segment improvement; do not compare directly with the 2,944-basket cohort.
- Raw/prepared hashes unchanged; rule counts independently checked, customer assignments aligned. All 20 tests passed at this stage; model/config/logs/manifest and run_models.ps1 saved.
- [EDA](eda_report.md), [experiment report](experiment_report.md), README/TODO updated: 97 completed, 60 pending. At this milestone test was reserved.

## Preparation milestone — 2026-11-17

- Investigate 33 nonstandard StockCodes, cancellations/returns/adjustments, duplicates, inconsistent names, large values, and 43 multi-timestamp invoices.
- Adopt policy 1.0 in configs/cleaning_policy.json and [policy](data_preparation_policy.md): retain approved merchandise, separate fees/vouchers/manual/auxiliary, first-occurrence exact deduplication assumption, all countries, no percentile caps.
- Produce 522,537 purchase lines, 19,372 separated ledger rows, 19,773 baskets, 517,289 invoice/product pairs, 3,907 full-period products. Raw SHA-256 unchanged.
- Retain 131,387 missing-ID purchase lines for global baskets. RFM uses fully identified train invoices: 3,145 profiles at cutoff 2011-08-01.
- Split whole invoices: training before August 1, validation before October 1, test before December 10. Use latest invoice timestamps; no training source line exceeds cutoff.
- Save original/log1p/standardized RFM, train parameters, 3,564 training products/names, and matrices retaining future zero-known rows.
- Reconcile rows, line/basket/RFM money, binary keys, one split/invoice. Check 37 product pairs from four invoices against raw and five RFM profiles against purchase lines; all match.
- All 14 tests pass: cutoff, future sales/returns, new products, missing IDs, conflicting invoices, binary presence. NPZ file closure fixed for Windows.
- [Preparation report](data_preparation_report.md), README/TODO updated: 50 completed, 107 pending.

At this milestone Monetary was explicitly gross, with three return-counterpart examples among ten largest-Quantity lines used only for investigation. Models/K/support selection and chart EDA had not yet run.

## Download and raw-audit milestone

- Download UCI ZIP, copy completed download into data/raw, verify CRC, extract workbook.
- Save source_metadata.json with URLs, timestamp, download method, sizes, ZIP/workbook SHA-256. Workbook hash unchanged before/after audit.
- Use fallback Python 3.12.14, pandas 3.0.1, numpy 2.3.5, openpyxl 3.1.5; do not modify runtime dependencies. Record requirements-audit.lock.txt.
- Measure 541,909 rows, eight columns, 25,900 invoice IDs including cancellations, 4,070 product codes, 4,372 nonmissing CustomerIDs.
- Find 135,080 missing CustomerIDs, 1,454 missing Descriptions, 5,268 exact duplicates, 9,288 C/c rows, 10,624 negative-Quantity rows.
- UnitPrice: two negative, 2,515 zero. There are 43 multi-timestamp invoices, none with multiple nonmissing CustomerIDs.
- Save raw_audit.json, raw_schema.csv, raw_monthly_counts.csv, raw_country_counts.csv, raw_numeric_summary.csv and [audit report](raw_audit_report.md).
- All seven tests pass (three audit/four downloader); monthly/country totals reconcile, raw hashes/internal links checked.
- TODO at that time: 17 completed, 140 pending. Cleaning/baskets/RFM/models not yet done.

PyPI DNS was unavailable; the audit runtime lacked sklearn/mlxtend/plotting. At that time raw_audit_ready=true, modeling_ready=false.

## Initial setup — before successful download

- Read the initial checklist and create TODO.md as the active project tracker.
- Draft proposal v0.1: problem, users, three RQs, methods/evaluation/deliverables, sample schedule.
- Record missing course requirements/unassigned roles; do not invent deadlines, rubric, required tools.
- Read UCI, relevant original RFM-study sections, and official rule documentation; save references.
- Create the dictionary from source schema without invented measured values.
- Create structure/README/candidate settings, Python 3.13.15 virtual environment, and environment checker.
- Implement protected SHA-256 download, immutable raw audit, setup.

| Attempt | Observed result | Impact at that time |
|---|---|---|
| pip install from PyPI | pypi.org DNS failure | No analysis packages or requirements.lock.txt |
| UCI ZIP download through Python | archive.ics.uci.edu DNS failure | No archive/workbook/source metadata |
| Environment check | ready=false, seven packages missing | Standard Python tools only |

No real-data/mining/clustering results were generated at initial setup. Downloader fixtures were temporary, not the dataset and not stored in data/raw.

Initial checks: all four offline downloader tests passed (extract/hash/offline rerun; altered-raw detection; conflicting-workbook preservation; failed-download cleanup). Scripts compiled, --help worked, links/JSON/UTF-8 were valid. Actual audit stopped for missing pandas, without fabricated statistics. TODO: ten completed including topic selection, 147 pending.
