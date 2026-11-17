# Association-rule and customer-segmentation experiments

> Scope: training/validation results at configuration selection. Final test has since been evaluated with frozen models; see [final evaluation](final_evaluation_report.md) and [consolidated report](../report/project_report.md). Historical statements about a reserved test refer to this earlier milestone.

## 1. Design and environment

- Backend: Weka 3.8.7 through src/WekaExperimentBridge.java. Python/pandas/numpy independently checks counts, computes metrics, and creates tables; ReportLab/Sharp produced 15 SVG/PNG figures at this stage. scikit-learn/mlxtend were not installed.
- Train: 11,044 baskets, 3,564 products, 3,145 RFM customers. Validation: 2011-08-01 to before 2011-10-01. Test: 2011-10-01 to before 2011-12-10, reserved at this stage.
- Quality auditing inspected full-period structure/anomalies; test was not unseen in every sense. Test did not mine rules or select K.
- Protocol/selection criteria: configs/experiment_protocol.json. Resource failures are recorded as timeouts, with a matched training-sample comparison.

## 2. Apriori and FP-Growth: correctness and resources

Weka uses nominal absent/present values. Apriori sets treatZeroAsMissing=true; FP-Growth selects present. Only positive presence is mined. Keep every invoice, including baskets without products meeting the threshold. Both algorithms prune below-threshold singleton columns using the same rule.

Weka Apriori rounds support×N; FP-Growth takes ceil. Required count is ceil(requested_support×N), with internal fraction (count−0.25)/N and independent count verification. Both algorithms mine unbounded itemset lengths for matched benchmarking, then export rules with at most three total items. This is not a bounded-max-len=3 Apriori benchmark.

| Requested support | Minimum train count | FP exported rules ≤3 items | Full-train Apriori |
|---|---:|---:|---|
| 1% | 111 | 3,242 | Not completed within 45 seconds wall time; no partial results |
| 2% | 221 | 218 | Not completed within 45 seconds wall time; no partial results |
| 5% | 553 | 0 | Completed; identical rules/counts |

FP-Growth completed three repetitions at each threshold. Apriori completed three at 5%; at 1%/2%, remaining repetitions were skipped after one timeout. No completion times were fabricated. The 45-second budget includes startup/input reading; successful benchmark timings combine fit and rule generation, without separate mining/generation or memory measurements.

For a nonempty matched comparison, sample 500 training invoices without replacement with seed 42, retaining row indices. Run three repetitions with alternating algorithm order:

| Sample support | Rules ≤3 items per algorithm | Counts and rule sets | Apriori median ms | FP-Growth median ms |
|---|---:|---|---:|---:|
| 2% | 800 | Identical; independently verified counts | 3,840.56 | 71.50 |
| 5% | 4 | Identical; independently verified counts | 50.84 | 16.38 |

![Figure 9. Matched 500-invoice runtime; implementation/hardware-dependent.](../results/figures/15_paired_subset_runtime.png)

Python bitsets verify counts independently, rather than merely comparing two implementations. A five-invoice fixture also yielded four identical rules. These local measurements do not establish that Apriori is always slower.

## 3. Validation-based rule selection

The 18 configurations combine support 1%/2%/5%, reported length 2/3, confidence 0.3/0.5/0.7, lift≥1.1, count≥20, and one consequent item. Rank by validation HitRate@5, breaking ties by fewer rules, shorter length, higher support, then higher confidence.

Task: offline basket completion. For invoices with at least two distinct items, hide one using a fixed invoice/seed hash. Unseen products may be hidden and remain in the denominator. Candidates come from train; exclude observed items and fill missing top-five positions with training popularity using the same policy for all methods. This does not predict click order or revenue gains.

There are 2,944 eligible validation baskets, including 188 hidden targets outside the training vocabulary. With one hidden target, HitRate@5 and Recall@5 coincide and are not independent evidence.

| Selected configuration/result | Value |
|---|---:|
| Minimum support | 1% |
| Maximum total rule items | 2 |
| Minimum confidence | 0.3 |
| Rules | 738 |
| HitRate@5 | 405/2,944 = 13.76% |
| Popularity baseline | 82/2,944 = 2.79% |
| At least one rule-based recommendation | 84.31% |

![Figure 10. Leading validation configurations and popularity baseline.](../results/figures/12_validation_rule_selection.png)

These selection-set results may be optimistic. Final-test findings are reported separately; no sales-impact claim follows.

### Rules with substantial evidence

| StockCode rule | Train count | Support | Train confidence | Train lift | Validation count | Validation confidence |
|---|---:|---:|---:|---:|---:|---:|
| 22386 → 85099B | 509 | 4.61% | 68.41% | 6.27 | 152 | 65.52% |
| 22697 → 22699 | 483 | 4.37% | 74.88% | 12.44 | 127 | 76.51% |
| 21931 → 85099B | 440 | 3.98% | 59.38% | 5.44 | 134 | 63.81% |
| 22411 → 85099B | 421 | 3.81% | 59.55% | 5.46 | 117 | 55.45% |
| 22383 → 20725 | 378 | 3.42% | 49.93% | 5.93 | 140 | 53.03% |

Support(A→B)=count(A∪B)/N; confidence(A→B)=count(A∪B)/count(A); lift(A→B)=confidence(A→B)/(count(B)/N). Hand-check fixture: among five baskets A appears in four, B in three, both in two; support=2/5=0.4, confidence=2/4=0.5, lift=0.5/(3/5)=0.8333. This validates formulas, not dataset findings.

The first rule is JUMBO BAG PINK POLKADOT → JUMBO BAG RED RETROSPOT. Co-occurrence does not prove purchasing the first item causes the second purchase.

## 4. K-means on training RFM

Use the three previously training-fitted log1p/standardized features. Weka K-means++ tests K=2–8, five seed groups 42–46, retaining the lowest-SSE solution from 20 starts per group; maximum 300 iterations, one execution slot. Disable Weka's internal distance normalization. Total: 700 initializations.

Euclidean silhouette uses all 3,145 training customers. SSE is independently recomputed from centroids/assignments. Stability is mean pairwise ARI between seed groups, not matching arbitrary cluster numbers. Eligible K requires smallest cluster≥3% and mean ARI≥0.8. Maximize mean silhouette; within 0.005, prefer smaller K.

| K | Mean silhouette | Mean SSE | Mean ARI | Minimum cluster fraction across seeds |
|---|---:|---:|---:|---:|
| 2 | 0.4440 | 4,857.85 | 0.9954 | 33.13% |
| 3 | 0.3513 | 3,642.06 | 0.9995 | 15.39% |
| 4 | 0.3673 | 2,849.69 | 1.0000 | 13.70% |
| 5 | 0.3353 | 2,442.87 | 0.9810 | 5.88% |
| 6 | 0.3236 | 2,164.59 | 0.9234 | 5.98% |
| 7 | 0.2771 | 1,941.35 | 0.9795 | 5.91% |
| 8 | 0.2778 | 1,779.75 | 0.9947 | 5.31% |

Select **K=2**, mean silhouette 0.4440, ARI 0.9954. These are internal criteria with interpretation, not accuracy against true segment labels.

![Figure 11. SSE declines with K, but silhouette does not improve correspondingly.](../results/figures/08_k_selection.png)

![Figure 12. PCA is illustrative; clustering uses all three features.](../results/figures/09_train_cluster_projection.png)

| Segment | Customers | Median R, days | Median F, invoices | Median M, GBP | Training gross purchase share |
|---|---:|---:|---:|---:|---:|
| Segment_1 | 1,048 | 19 | 5 | 1,639.80 | 79.90% |
| Segment_2 | 2,097 | 102 | 1 | 315.00 | 20.10% |

![Figure 13. Segment profiles in original RFM units.](../results/figures/10_segment_profiles.png)

Segment_1 is more recent, frequent, and higher in gross purchases; Segment_2 has the opposite relative profile. Neither verified churn nor profitability labels are justified because Monetary excludes neither returns nor costs.

## 5. Linking segments and rules

Freeze pre-cutoff customer profiles rather than rebuilding RFM using the future. Mine global and segment rules on the same training-profile cohort, reusing selected global parameters. Count threshold=max(ceil(support×group baskets),20), so small groups may receive a higher effective relative support.

| Mining group | Train baskets | Validation baskets | Retained rules | Minimum count |
|---|---:|---:|---:|---:|
| global_identified | 10,075 | 2,449 | 455 | 101 |
| Segment_1 | 6,955 | 1,694 | 574 | 70 |
| Segment_2 | 3,120 | 755 | 230 | 32 |

Comparison uses 2,274 eligible validation baskets from the same cohort. Another 708 new/unprofiled-customer invoices are reported separately, without invented segments. Do not directly compare these rates with 13.76% above because the cohorts differ.

| Method | HitRate@5 | Hits/baskets | Rule coverage |
|---|---:|---:|---:|
| popularity | 2.81% | 64/2274 | 0.00% |
| global_rules_identified | 14.51% | 330/2274 | 77.04% |
| segment_rules | 14.07% | 320/2274 | 76.74% |

![Figure 14. Same baskets, hidden targets, and fallback for all three methods.](../results/figures/13_segment_rule_comparison.png)

**Segment rules do not outperform global rules on this validation cohort.** Segments describe behavior, but partitioning data does not guarantee recommendation improvement. Do not change seed/K merely to obtain a favorable result. Statistical uncertainty and final test were addressed in the later frozen evaluation.

## 6. Outputs and reproduction

- The 15 stage figures and EDA tables are under results/figures and results/tables/eda; final test adds figure 16.
- Rule grids/stability, profiles, and segment comparison: results/tables/models.
- Weka models and mapping/centroid metadata: results/models. ARFF inputs have three clustering features, without CustomerID as a feature.
- Logs/timeouts and experiment_manifest.json: results/experiments.
- Before final freezing, run `& .\scripts\run_models.ps1`; JAVA_EXE/WEKA_JAR override installation paths. Requirements: JDK/javac, Weka, Python numpy/pandas/reportlab/Pillow, Node/Sharp.
- The current training runner is blocked by the final freeze. Verify saved final results with run_final_evaluation.ps1; English documentation remains retained.

## 7. Limitations and later evaluation

Validation selects settings and is not an unbiased final estimate. The study covers one historical retailer; masked baskets are not real clicks, gross purchases can later be returned, and clusters may reflect a behavioral continuum. Local timings combine mining/rule generation without reliable memory measurements. No A/B experiment or revenue impact was measured.

The proposed next step at this milestone was freezing and one-time test evaluation. That step is now complete; see [final_evaluation_report.md](final_evaluation_report.md). Further model changes must not reuse the same test as an independent evaluation.

## Technical sources

- Weka SimpleKMeans: https://weka.sourceforge.io/doc.stable/weka/clusterers/SimpleKMeans.html
- Weka FPGrowth: https://weka.sourceforge.io/doc.stable/weka/associations/FPGrowth.html
- Silhouette: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html
- Rule formulas: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/
- UCI Online Retail: https://doi.org/10.24432/C5BW33.
