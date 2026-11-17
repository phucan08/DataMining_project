# Mining E-commerce Purchasing Behavior Using Association Rules and Customer Segmentation

Data Mining course project: mine joint purchases with Apriori/FP-Growth, segment customers with RFM/K-means, then compare global and segment-specific rules.

## Current status

- **Final test completed with frozen models:** global 458/5,183 = 8.84% HitRate@5; popularity 90/5,183 = 1.74%. On the same 3,579 training-profile customer baskets, segment rules reach 8.86% and identified-global rules 8.80%; the difference interval includes zero. No refitting or model reselection used test results.
- **Consolidated report:** [project_report.md](report/project_report.md). Details: [final_evaluation_report.md](docs/final_evaluation_report.md). There are 16 PNG/SVG figure pairs and 24 passing tests.
- Raw download/audit: 541,909 rows, eight columns; archive/workbook SHA-256 retained.
- Policy 1.0 preparation: 522,537 valid merchandise lines, 19,773 baskets, 3,145 training RFM profiles.
- Training/validation experiments: 18 rule configurations; 738 selected rules, support 1%, confidence 30%, lift ≥1.1, two total items. Validation HitRate@5 is 13.76% versus popularity 2.79%.
- K-means tested K=2–8; K=2 selected, mean silhouette 0.444. Same-cohort validation segment/global scores are 14.07%/14.51%.
- Weka 3.8.7 runs algorithms; Python checks counts/metrics; ReportLab/Sharp renders figures. This workflow does not require scikit-learn/mlxtend.
- Full-train Apriori times out at 1%/2%; matched 500-invoice comparisons yield identical rules/counts.
- Rubric, deadline, team members, and required tools are still unknown.

[TODO.md](TODO.md) is the single progress checklist. Other documentation: [proposal](docs/proposal.md), [course requirements](docs/course_requirements.md), [data dictionary](docs/data_dictionary.md), [literature notes](docs/literature_notes.md), [progress](docs/progress.md), [raw audit](docs/raw_audit_report.md), [preparation report](docs/data_preparation_report.md), [cleaning policy](docs/data_preparation_policy.md), [EDA](docs/eda_report.md), and [training/validation experiments](docs/experiment_report.md). The obsolete duplicate checklist was removed.

## Project structure

| Path | Contents |
|---|---|
| docs/ | Proposal, requirements, dictionary, policies, literature, stage reports, progress |
| scripts/ | Setup, download, audit, preparation, experiments, verification, reporting |
| configs/ | Cleaning policy, cutoffs, experiment/final-evaluation protocols, selected settings |
| data/raw/ | Original archive/workbook and source metadata |
| data/processed/ | Purchase/exclusion ledgers, baskets, coordinate arrays, training RFM |
| src/, tests/ | Processing/metric/plotting code, Weka Java bridge, meaningful tests |
| results/tables/, results/figures/ | Audit/model/final-test tables and 16 PNG/SVG figure pairs |
| results/models/, results/experiments/ | Models, metadata, inputs/logs, benchmarks, provenance |
| report/ | Consolidated research report |
| notebooks/, slides/ | Reserved for course-dependent deliverables |

## Windows PowerShell workflow

Run commands from the project directory. The failed local pip-only virtual environments and disposable build/cache files have been removed. Runners can use the existing analysis runtime or an explicitly configured compatible environment.

### Verify saved final-test results

```powershell
& .\scripts\run_final_evaluation.ps1
```

The test was scored once using the 738 rules and K=2 retained from train. The runner validates source/data/model hashes against the freeze lock and saved outputs against the receipt. With a receipt present it returns saved results instead of rescoring. It retains the English final documentation and renders figure 16. Changed sources/results stop verification.

Current provenance: results/tables/final_test/evaluation_receipt.json and results/models/final_evaluation_lock.json. Historical training/validation JSON files retain test=false from selection time; configs/project.json records current status. Do not delete the freeze lock to tune on the used test. Use a separate workspace/artifact set for a new study.

### Raw audit and preparation

```powershell
& .\scripts\run_raw_audit.ps1
& .\scripts\run_preparation.ps1
```

Audit selects Python with pandas/numpy/openpyxl, verifies raw hashes, and produces tables. Preparation investigates anomalies, applies configs/cleaning_policy.json, reconciles totals, and writes derived data. It requires no scikit-learn/mlxtend. Keep the current frozen inputs intact; conduct a fresh full reproduction in a separate workspace. English report snapshots are retained after the final freeze.

Training ends exclusively at 2011-08-01, validation at 2011-10-01, and test at 2011-12-10. Entire invoices stay together. RFM, vocabulary, product names, and transformation parameters use train only. Single-item baskets and future rows without known items are retained.

Monetary measures merchandise purchases **before returns**, not net revenue/profit. Future returns do not delete past purchases; some large transactions have reversal evidence.

### Read prepared outputs

```python
import numpy as np
import pandas as pd

rfm = pd.read_csv('data/processed/rfm_train.csv', dtype={'CustomerID': 'string'})
catalog = pd.read_csv('data/processed/product_catalog_train.csv', dtype={'StockCode': 'string'})
baskets = pd.read_csv('data/processed/baskets.csv', dtype={'InvoiceNo': 'string', 'CustomerID': 'string'})
with np.load('data/processed/basket_train_coordinates.npz') as matrix:
    shape = matrix['shape'].tolist()
    row_indices = matrix['row_indices'].copy()
    column_indices = matrix['column_indices'].copy()
    present = matrix['values'].copy()
```

NPZ contains project-specific COO arrays, not scipy.sparse.save_npz files. Row mappings are in basket_*_row_index.csv, columns in product_catalog_train.csv by ColumnIndex, and Present is always 1. Read identifiers as strings.

### Training workflow before the final freeze

```powershell
& .\scripts\run_models.ps1
```

**The current workspace stops this runner because artifacts are frozen.** Before freezing, it exports inputs, compiles the Java bridge, runs experiments, checks counts, selects settings, and creates figures/reports/tests. It does not score final test. K-means uses 700 initializations. Apriori gets 45 seconds wall time per attempt; timeouts are recorded, never partial results. Timings combine fit and rule generation; memory and separate mining time are not measured.

Requirements: Python with pandas/numpy/openpyxl/reportlab/Pillow; JDK with java/javac; Weka; Node with Sharp. Set CODEX_PRIMARY_RUNTIME_PYTHON and CODEX_PRIMARY_RUNTIME_NODE for compatible runtimes as needed, and CODEX_PRIMARY_RUNTIME_NODE_MODULES to the Node module directory. requirements-experiments-python.lock.txt records Python package versions; results/tables/model_environment.json records Python/Java and the Weka jar hash.

Default paths can be overridden:

```powershell
$env:JAVA_EXE = 'D:\java 25\bin\java.exe'
$env:WEKA_JAR = 'D:\Weka-3-8-7\weka.jar'
```

Key outputs: selected_global_rules.csv, selected_rule_config.json, clustering_k_comparison.csv, cluster_profiles.csv, segment_vs_global_validation.csv under results/tables/models; selected_weka_kmeans.model under results/models. The training scaler is data/processed/rfm_transform.json. PNG is convenient for slides; SVG supports scaling.

### Optional Python setup when networking works

Python 3.11+ and HTTPS access to PyPI/UCI are needed for a new installation. A local environment is created only when setup is run:

```powershell
& .\scripts\setup.ps1
& .\.venv\Scripts\python.exe scripts/download_data.py
& .\.venv\Scripts\python.exe scripts/audit_data.py
```

Equivalent commands without activation or changing execution policy:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check --retries 0 --timeout 15 -r requirements.in
# Only after installation succeeds:
& .\.venv\Scripts\python.exe -m pip freeze | Set-Content requirements.lock.txt -Encoding utf8
& .\.venv\Scripts\python.exe scripts/check_environment.py
```

requirements.in is the optional broad Python stack. requirements.lock.txt is created only after successful installation; the actual audit and Weka-workflow dependencies are recorded in their separate lock files. requirements-audit.lock.txt can be installed in .venv-audit, which audit runners recognize.

For browser download, use [UCI](https://archive.ics.uci.edu/dataset/352/online+retail), save data/raw/online_retail.zip, and rerun download_data.py. It verifies/extracts the actual workbook and creates source metadata.

### Evidence and tests

- data/raw/source_metadata.json: source URLs, timestamp, license, size, SHA-256.
- results/tables/raw_audit.json, raw_schema.csv, raw_monthly_counts.csv, raw_country_counts.csv, raw_numeric_summary.csv: observed audit evidence.
- results/tables/environment.json: package readiness; distinguish raw_audit_ready, modeling_ready, and the optional Python-stack ready flag.
- results/tables/final_test/: saved predictions, metrics, bootstrap intervals, cohort/rule audits, receipt.
- results/final_delivery_manifest.json: current documentation/delivery hashes.

With a compatible Python executable:

```powershell
python -B -m unittest discover -s tests -v
```

Use -B (or PYTHONDONTWRITEBYTECODE=1) to avoid recreating Python bytecode caches. Tests cover download protection, audit, split boundaries, future-information leakage, binary baskets, rule counts, clustering metrics, paired evaluation, and frozen-artifact integrity. Fixtures do not replace real-data auditing.

## Methodological principles

- Keep raw immutable and measure actual data rather than copying dataset-page counts.
- Split chronologically by whole invoice.
- Train RFM/segments only before the cutoff.
- Compare Apriori/FP-Growth with identical data/thresholds; equal conditions should not imply different rule quality.
- Never invent CustomerIDs; report ineligible cohorts separately.
- No clustering accuracy without labels; co-occurrence does not establish revenue gains.

## Data and references

Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33. CC BY 4.0. Reviewed literature is in [literature_notes.md](docs/literature_notes.md). Distinguish proposed work, measured findings, and unconfirmed course requirements.
