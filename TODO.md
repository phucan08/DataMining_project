# TODO — Mining E-commerce Purchasing Behavior Using Association Rules and Customer Segmentation

## Current progress — 2026-11-18

Available: [proposal](docs/proposal.md), [unconfirmed course requirements](docs/course_requirements.md), [data dictionary](docs/data_dictionary.md), [literature notes](docs/literature_notes.md), README, and project structure. See [progress log](docs/progress.md).

**Data complete:** official UCI download, CRC/SHA-256 checks, raw audit, anomaly investigation, policy 1.0. Raw/prepared hashes remain unchanged after experiments.

**Preparation complete:** 522,537 merchandise purchase lines, 19,773 baskets, RFM for 3,145 training customers, sparse vocabulary/matrices, training-fitted RFM transformations. See [preparation report](docs/data_preparation_report.md) and [policy](docs/data_preparation_policy.md).

**EDA, experiments, and final test complete:** 16 PNG/SVG figure pairs; 738 rules and K=2 frozen before scoring; all-test HitRate@5 8.84% versus popularity 1.74%. Same-cohort comparisons do not demonstrate segment improvement. Customer bootstrap, consolidated reporting, and 24 passing tests are available. See [research report](report/project_report.md) and [final evaluation](docs/final_evaluation_report.md). Rubric/deadline/team, slides, and course-formatted submission remain pending.

### Completed final-test milestones

- [x] Freeze models, rules, scaler, source data, and evaluator before final test.
- [x] Score test once, retain unseen targets, report cohorts/fallback and customer-bootstrap intervals.
- [x] Save receipt/hashes; verify repeat calls neither rescore nor change training artifacts.
- [x] Consolidate results/RQs/limitations in report/project_report.md; do not treat it as a submitted course-approved version.

## 0. Status and usage

- [x] Select topic: **Mining E-commerce Purchasing Behavior Using Association Rules and Customer Segmentation**.
- [ ] Confirm the title with the instructor under class registration procedures.

This is a proposed plan, not the official rubric. Completed tasks have checkable outputs. Unchecked tasks include final-stage requirements and optional extensions. Adjust the sample schedule when the deadline/team size is known.

For each task, add an owner, target date, and evidence path. Mark complete only with a verifiable output. One person may cover several roles. TODO.md is the single active checklist; the obsolete duplicate was removed.

## 1. Proposed scope

**Goal:** discover products purchased together; segment customers by purchase history; compare patterns between segments and propose applications.

1. **RQ1:** Which co-purchase rules have sufficient evidence and practical meaning?
2. **RQ2:** Which RFM/K-means customer segments are stable and interpretable?
3. **RQ3:** How do segment-specific rules differ from global rules?

**Core:** data/cleaning log; EDA; Apriori/FP-Growth; RFM/K-means; segment rules; evaluation/report/slides/reproducible code.

**Extensions:** offline recommendations, a second clustering algorithm, dashboard/demo. Offline evaluation is mandatory for claims of recommendation improvement.

**Limit:** historical analysis does not prove bundles increase revenue or features cause behavior. There is no live sales experiment.

## 2. Stage 1 — Requirements and proposal

- [ ] Obtain brief/rubric: deadline, team size, report format/length, presentation time, demo, submission channel.
- [ ] Confirm required Weka/custom implementations/specific algorithms or self-collected data.
- [ ] Confirm citation and assistance-disclosure requirements.
- [x] Describe the problem, intended users, and decisions supported.
- [x] Fix the three RQs; revise after instructor feedback if needed.
- [x] Read at least one RFM/segmentation study and one rule-mining source; record relevance.
- [x] Draft a roughly 1–2-page proposal unless specified otherwise: background, goals, data, methods, evaluation, outputs, schedule.
- [x] Distinguish core/extensions; keep chatbots, payments, and a complete sales platform outside scope.
- [ ] Assign data/rules/segmentation/report/verification roles; cross-check outputs in a team.
- [ ] Record unclear requirements and confirm them before locking the method.

**Outputs:** proposal/responsibility table. **Gate:** understandable grading criteria and feasible team scope; register/approve the topic under class rules.

## 3. Stage 2 — Setup and data acquisition

- [x] Select UCI Online Retail; review description, license, citation.
- [x] Download officially; record URL/date/SHA-256.
- [x] Preserve raw; write derived versions separately.
- [x] Inspect actual rows/columns/date range/types/currency, rather than copying the dataset page.
- [x] Create the dictionary for InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country.
- [x] Create data/raw, data/processed, notebooks, src, configs, results/tables, results/figures, report, slides, and demo if needed.
- [x] Establish the actual backend: Python/pandas/NumPy/openpyxl for data, Weka 3.8.7 for algorithms, ReportLab/Sharp for charts. sklearn/mlxtend/matplotlib remain unavailable and unnecessary for this backend.
- [x] Export Weka inputs; separate Java algorithm execution from Python count/metric/table verification. Whether Weka is mandatory remains unconfirmed.
- [x] Record actual Python/library versions and reproducible environment files.
- [x] Write README with goals/data/setup/execution order.
- [ ] Set up code version storage; avoid unnecessary large data or account secrets.

**Outputs:** raw data/dictionary/README/working environment. **Gate:** a documented command can read the data.

## 4. Stage 3 — Audit and cleaning

- [x] Check per-column missingness, types, identifiers, dates, invalid rows.
- [x] Preserve InvoiceNo/StockCode/CustomerID as identifiers; avoid coercion loss and floating-ID artifacts.
- [x] Inspect cancellations, Quantity <=0, UnitPrice <=0, returns/adjustments.
- [x] Separate purchase and refund policies; understand negatives before deletion.
- [x] Build valid merchandise purchases excluding cancellations/returns/non-product entries.
- [x] Define gross versus net Monetary; adopted valid purchases before returns, not net revenue.
- [x] Inspect exact duplicates/repeated invoice products; distinguish errors from valid repeats.
- [x] Review shipping/discount/service codes; justify separation.
- [x] Review multiple Descriptions per StockCode; keep StockCode as key and choose consistent names.
- [x] Exclude missing CustomerIDs from RFM/customer analysis; retain eligible global baskets.
- [x] Check invoice/customer/date conflicts before basket construction. Verified 43 IDs differ by at most one minute; use latest timestamp and one split per invoice.
- [x] Inspect quantity/price/invoice-value outliers; do not remove wholesale customers solely for high value.
- [x] Decide all-country versus main-market scope and explain generalization implications.
- [x] Log ordered before/after rows/invoices/products/customers; raw issue groups may overlap.
- [x] Export clean purchases/log; compare sample invoices with raw.

**Outputs:** clean purchases/ordered audit. **Gate:** explain retention/exclusion and reconcile counts with code.

## 5. Stage 4 — EDA and chronological evaluation design

- [x] Summarize invoices, identified customers, products, valid purchase value, basket length.
- [x] Plot orders/value over time and label partial months.
- [x] Analyze popularity by invoices containing a product, separately from total Quantity.
- [x] Analyze invoice value, products/invoice, invoices/customer, purchase concentration.
- [x] Analyze country scale and possible wholesale behavior.
- [x] Interpret every plot; distinguish observations from hypotheses.
- [x] Fix T0<T1<T2<T3 using actual dates/volume: train [T0,T1), validation [T1,T2), test [T2,T3).
- [x] Use an approximate 60/20/20 starting idea only if helpful; save explicit dates after density review. Actual August 1/October 1 boundaries are not an exact ratio.
- [x] Keep entire invoices in one period; never randomly split product lines.
- [x] Learn product lists/transforms/features from train; choose settings with validation.
- [x] Reserve final test for one frozen evaluation; no test-based min_support/K/filter reselection. Freeze occurred before scoring.
- [x] Keep pre-T1 models/segments for validation/test; evaluate segment rules on pre-T1 profiles and report new customers. Both stages used frozen settings.
- [x] Distinguish full-period descriptive EDA from held-out evaluation; do not claim completely unseen test if EDA informed choices.

**Outputs:** EDA figures/summaries/dated protocol. **Gate:** distinguish discovery/selection/held-out data.

## 6. Stage 5 — Baskets and RFM

### A. Baskets

- [x] Group valid product lines by InvoiceNo using StockCode items.
- [x] Encode presence=1/absence=0; Quantity never duplicates presence.
- [x] Manually inspect invoices and converted basket totals.
- [x] Report single-item baskets; exclude only with explicit population/support definitions.
- [x] If pruning rare products for resources, use training thresholds and preserve denominators. Saved vocabulary retains all train products; mining safely prunes singleton columns below support while retaining every basket.
- [x] Estimate matrix size/use sparsity where appropriate; save code/name mappings.

### B. Customer RFM

- [x] Use a consistent T1 reference date and pre-T1 history only.
- [x] Calculate Recency as days from last purchase; lower means more recent.
- [x] Calculate Frequency as distinct valid purchase invoices, not product lines.
- [x] Calculate Monetary as summed Quantity × UnitPrice under the adopted policy.
- [x] Export one row/customer; hand-check low/high-frequency examples.
- [x] Plot R/F/M distributions; inspect invalid values/outliers.
- [x] Use log1p where distribution/domain justify it, never blindly on negative Monetary.
- [x] Standardize before K-means; fit transforms/scaler only on train.
- [x] Save original/transformed RFM and feature definitions/configuration.

**Outputs:** invoice-item matrix/customer-RFM table. **Gate:** correctly represent invoices versus customers.

## 7. Stage 6 — Global association rules

- [x] Document support/confidence/lift and hand-calculate a small check.
- [x] Run a small Apriori fixture; do not treat fixture findings as final.
- [x] Choose a modest support/length grid with explicit minimum basket counts.
- [x] Compare Apriori/FP-Growth on identical data/vocabulary/support/length scope. Full-train timeout attempts and matched 500-basket runs mine unbounded lengths then export up to three items.
- [x] Compare frequent sets/support with canonical ordering; investigate settings/data/float discrepancies. Rule unions/counts were independently matched; a separate complete singleton-itemset export remains absent.
- [ ] Time itemset mining separately from rule generation and document memory methods if measured. Currently combined Weka fit+generation only; no separate memory measurement.
- [x] Repeat timings under the same environment and explain aggregation; avoid universal speed claims from one run.
- [x] If Apriori is too expensive, declare timeouts and compare a reproducible identical subset, never unmatched datasets.
- [x] Filter rules by confidence/lift/count/side length.
- [ ] Review rare high-lift, redundant, and impractical rules; do not select only the first lift-ranked rows.
- [x] Select on train/validation and log every tried configuration.
- [x] Freeze selected rules; recompute held-out counts/support/confidence/lift, flag zero denominators/weak evidence. Validation and frozen final test are complete.
- [x] Explain 5–10 supported representative rules with product names/business meaning; do not force a target rule count.
- [ ] Save itemsets, full/filtered rules, benchmarks, and threshold-sensitivity figures.

**Outputs:** global rules/algorithm comparison/RQ1. **Gate:** verify actual counts and distinguish runtime from rule quality.

## 8. Stage 7 — RFM/K-means segmentation

- [x] Run K-means on prepared RFM and record actual seeds/initialization settings.
- [x] Test a small feasible K range, e.g. 2–8.
- [x] Record inertia/elbow/silhouette/sizes; document seed/method for any silhouette sampling.
- [x] Test multiple seeds; compare partitions with ARI, not numeric label IDs.
- [ ] Assess a manageable set of reasonable transformation/outlier alternatives and their selection data.
- [x] Select K using separation/stability/size/interpretability, not appearance or silhouette alone.
- [x] Tabulate customer counts/shares, original median R/F/M, purchase-value shares.
- [x] Name clusters from measured behavior, e.g. recent/frequent/higher purchases.
- [x] Treat long inactivity as Recency description, not verified churn.
- [ ] Add RFM boxplots and a cluster overview; label PCA as illustration. PCA/median charts exist; cluster boxplots remain supplementary.
- [x] Save model/scaler/customer assignments/configuration and reproduce assignments.
- [ ] Treat Agglomerative/DBSCAN as optional; do not assume new-customer assignment works like K-means.

**Outputs:** profiles/figures/RQ2. **Gate:** interpret original RFM without claiming ground-truth accuracy.

## 9. Stage 8 — Integrate rules and segments

- [x] Join training invoices to CustomerID/cluster; explain unmatched cases.
- [x] Retain all-basket global rules and add an identified-cohort global model for fair segment comparison.
- [x] Count baskets/customers per group and flag insufficient data.
- [x] Mine per-group rules; record relative support and absolute supporting counts.
- [ ] Compare common/group-specific rules and confidence/lift differences with sufficient evidence.
- [x] Use pre-T1 labels in later periods; never back-assign history using future RFM.
- [x] Recompute fixed segment-rule evidence on validation/test; report sparse/new-customer groups. Both stages now have count/support/confidence/lift tables.
- [x] Suggest evidence-linked bundles/cross-sells/category applications; separate observations/hypotheses/actions to test.
- [x] Report no improvement/instability honestly, with possible explanations, rather than forcing expectations.

**Outputs:** global/segment comparison/RQ3. **Gate:** link both analyses on compatible cohorts.

## 10. Stage 9 — Conditional recommendation evaluation extension

Required for recommendation-improvement claims. The task measures offline basket completion, not real click sequence or incremental revenue.

- [x] Fix training-popularity, global-rule, and segment-rule methods.
- [x] Match eligible customers/baskets, candidates, recommendation K, and fallback.
- [x] Hide items deterministically in held-out baskets with at least two products; use remaining items as input.
- [x] Exclude observed products, deduplicate, and fix multi-rule score aggregation.
- [x] Set recommendation K/ranking using validation; freeze before final test. The implemented protocol uses K=5.
- [x] Define Recall/HitRate/Precision@K and coverage, denominators, and short-list treatment. Final-test tables include all these metrics.
- [x] State that one hidden target makes Recall and HitRate equal, not independent evidence.
- [x] Report single-item baskets, unseen products/new customers, no-rule cases, fallback rates.
- [x] Compare global/segment on identical pre-cutoff-profile cohorts; report overall fallback-inclusive results separately.
- [x] Bootstrap by customer when feasible, since their invoices are not independent.
- [x] Save overall/segment metrics, eligible counts, and representative errors.

**Outputs:** baseline comparison/reproducible protocol.

## 11. Stage 10 — Demo and reproducibility

### Demo, depending on rubric/time

- [ ] Choose a narrow flow: basket/rules/recommendations or sample customer/RFM/segment.
- [ ] Display product names, rule metrics, short explanations; show segments only for valid profiles.
- [ ] Handle empty inputs, unmatched products, and new customers using agreed messages/fallback.
- [ ] Load fitted results instead of heavy mining per click.
- [ ] Test offline if data/models are already available.

### Required verification

- [ ] Remove notebook hidden-state dependencies; restart and run in order.
- [x] Check meaningful invariants: whole-invoice splits, one RFM row/customer, invoice-based Frequency, support denominators, cutoff-safe features.
- [x] Compare hand-calculated support/confidence/lift/RFM with code.
- [ ] Reproduce raw-to-main-tables/figures per README, preferably independently/in a fresh environment.
- [x] Record official config/seed/versions/timing/artifacts; do not mix undocumented runs.
- [ ] Trace every reported value to generated tables/figures; round only for presentation.

**Outputs:** reproducible workflow/demo if required. **Gate:** another reader can reproduce main findings from README.

## 12. Stage 11 — Report and documentation

Write from week one and update after each stage.

- [x] Write Abstract last, reflecting actual goals/methods/results/limitations.
- [x] Write Introduction: problem, RQs, scope, course-project contribution.
- [x] Write Related Work/background for rules/Apriori/FP-Growth/RFM/K-means with reviewed references.
- [ ] Complete Dataset/Preprocessing: source/dictionary/audit/returns/cohorts/process diagram.
- [x] Write Methodology: baskets/RFM/transforms/time split/algorithms/thresholds/integration.
- [x] Write Experimental Setup: environment/seeds/settings/metrics/selection protocol.
- [x] Answer each RQ in Results with measured tables/figures.
- [x] Write Discussion: insights/errors/resources/stability/unproven claims.
- [x] Write Limitations: one retailer/finite period/seasonality/wholesale/missingness/outliers/cold start/offline scope.
- [x] Write evidence-based Conclusion/Future Work without unsupported personalization claims.
- [ ] Add contribution table/parameter appendices if required.
- [ ] Review captions/units/terms/sources/contents/cross-references/course formatting.
- [ ] Reconcile values across notebooks/report/slides/demo.
- [ ] Export PDF and inspect every page for readability/overflow/blurred figures/missing formulas.

Recommended figures/tables: cleaning audit, time EDA, Apriori/FP benchmark, representative rules, K selection, segment RFM, global/segment comparison, recommendation baseline.

**Outputs:** editable/final PDF report/references/appendices. **Gate:** all conclusions have evidence within methodological limits.

## 13. Stage 12 — Defense, submission, completion

- [ ] Prepare slides for the allotted duration: problem/RQs/data/methods/findings/limits/conclusion.
- [ ] Prioritize results over general theory/interface explanations.
- [ ] Prepare answers about dataset/RFM/scaling/K/lift/returns/leakage/segment value.
- [ ] Explain identical Apriori/FP rules with different runtimes.
- [ ] Prepare answers on new customers, small baskets, rare products, outliers, unsupported conclusions.
- [ ] Rehearse with timing; team members understand the full pipeline and assigned sections.
- [ ] Prepare genuine backup demo images/video if required/allowed.
- [ ] Freeze the submission version; distinguish official results from trials/temp files.
- [ ] Package code/notebooks/environment/config/README/report/slides/required tables/figures.
- [ ] Include download instructions or permitted data; check submission size limits.
- [ ] Extract elsewhere and verify paths/files; remove machine-specific assumptions.
- [ ] Recheck rubric, filenames, team details, format, deadline/time zone.
- [ ] Submit through the course channel when instructions are available; verify/save confirmation.
- [ ] Back up the submitted version/code/data/config/results; prepare the defense.
- [ ] Record defense feedback; make/re-submit required revisions with versioned confirmation.

**Complete only when:** rubric satisfied, reproducibility checked, report/slides consistent, submission confirmed, defense completed if required, and mandatory revisions resolved.

## 14. Illustrative four-week schedule

| Week | Main work | Checkpoint |
|---|---|---|
| 1 | Requirements/proposal/setup/data/cleaning/EDA/split | Clean data/audit/RQs/protocol |
| 2 | Baskets/RFM/Apriori–FP/K-means | Initial rules/profiles |
| 3 | Segment rules/held-out checks/errors/recommendation evaluation | Frozen configuration/official findings |
| 4 | Reproduction/report/slides/required demo/defense rehearsal | Submission package; 2–3 buffer days if feasible |

This is a workload template, not a runtime promise or a precise estimate for an unknown team size.

## 15. Priorities under time pressure

1. Correct data/audit/RQs and leakage-safe evaluation.
2. Global rules, RFM/K-means, and segment integration.
3. Evaluation/limitations/reproducibility.
4. Report/slides/on-time submission.
5. Small demo if mandatory; otherwise after research.
6. Drop extra clustering/elaborate interfaces/large grids before core steps.

## 16. Original first-five tasks

- [ ] Obtain rubric/deadline/tool requirements.
- [x] Draft the three-RQ proposal.
- [x] Download Online Retail, preserve raw, create dictionary.
- [ ] Create a quality/cleaning-audit notebook.
- [x] Fix valid-purchase policy, country scope, time boundaries.

## 17. Official references

- UCI: https://archive.ics.uci.edu/dataset/352/online+retail
- Original RFM study linked by UCI: Chen, Sain, Guo (2012), “Data mining for the online retail industry: A case study of RFM model-based customer segmentation using data mining.” Read before citing.
- Rules: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/
- Apriori: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/apriori/
- FP-Growth: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/fpgrowth/
- Clustering: https://scikit-learn.org/stable/modules/clustering.html

Checklist examples are generic plans. Actual settings/selected values are in configs/experiment_protocol.json, configs/project.json, and experiment reports; do not treat every example above as a completed experiment.

