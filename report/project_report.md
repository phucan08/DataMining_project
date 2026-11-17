# Mining E-commerce Purchasing Behavior Using Association Rules and Customer Segmentation

Research report — complete analytical content. Team/member details and course-specific formatting must be added before submission.

## Abstract

This project analyzes UCI Online Retail using association rules and RFM customer segmentation. After quality checks, 522,537 valid merchandise lines form 19,773 baskets. Training history before 2011-08-01 supplies rule mining and RFM for 3,145 customers; August–September validation selects settings; October–December 9 test is evaluated once with frozen models. The selected configuration contains 738 rules and K-means K=2. On 5,183 eligible test baskets, global rules achieve HitRate@5 of 8.84%, versus 1.74% for training popularity. On the same 3,579 training-profile customer baskets, segment rules achieve 8.86% and identified-global rules 8.80%; the bootstrap difference interval does not establish improvement. Segmentation supports behavioral description but has not demonstrated better recommendations.

## 1. Problem and research questions

The objectives are to identify products frequently purchased together, describe customer differences, and test whether combining these analyses helps offline basket completion. Association rules analyze invoices; clustering analyzes customers.

1. **RQ1:** Which co-purchase rules have sufficient evidence and usefulness for basket completion?
2. **RQ2:** Which RFM/K-means segments are stable and interpretable?
3. **RQ3:** How do segment rules differ from global rules, and do they improve results on the same cohort?

### Related work

Chen, Sain, and Guo (2012) combine RFM, K-means, and customer interpretation in retail data. This project adopts RFM representation and original-unit interpretation, adding co-purchase rules and chronological evaluation. The original study has geographical fields absent from the selected UCI schema; its cluster counts/performance are not copied as project findings. Weka documentation describes the implemented algorithms. Rule formulas were checked against mlxtend documentation, although the actual backend is Weka.

## 2. Data and preprocessing

Source: Chen, D. (2015), *Online Retail*, UCI Machine Learning Repository, DOI 10.24432/C5BW33, CC BY 4.0. The actual raw workbook has 541,909 rows and eight columns. Invoice/product/customer values remain identifiers; raw SHA-256 is preserved.

The policy separates cancellations, nonpositive Quantity/UnitPrice, services, vouchers, and manual adjustments. Exact duplicates retain their first occurrence under an explicit assumption. Unusual real-product codes are reviewed before retention. All countries and large transactions are retained without percentile caps. Missing CustomerID is acceptable for valid global baskets but excluded from RFM. The invoice timestamp is the latest line timestamp, preventing an invoice from crossing a cutoff.

Prepared data contain 522,537 purchase lines, 19,773 baskets, and 517,289 invoice/product pairs. Monetary is merchandise purchases **before returns**, not profit or net revenue. Future returns never delete a past training purchase.

Evidence: [raw audit](../docs/raw_audit_report.md), [policy](../docs/data_preparation_policy.md), [preparation report](../docs/data_preparation_report.md), and [data dictionary](../docs/data_dictionary.md).

## 3. Chronological design and EDA

| Period | Interval | Baskets | Purpose |
|---|---|---:|---|
| Train | 2010-12-01 to before 2011-08-01 | 11,044 | Vocabulary, rules, RFM, scaler, K-means |
| Validation | 2011-08-01 to before 2011-10-01 | 3,157 | Rule-parameter selection |
| Test | 2011-10-01 to before 2011-12-10 | 5,572 | One frozen evaluation |

EDA covers time, basket-size/value distributions, product popularity, countries, and RFM. December 2011 ends on the 9th and is not a complete month. Popularity counts invoices containing a product, not total Quantity. The top 10% of training customers contribute about 58.97% of gross purchases. RFM has long right tails, motivating log1p and training-only standardization.

![Training RFM distributions](../results/figures/05_train_rfm_distributions.png)

Full-period descriptive auditing inspected data structure, so test is not described as unseen in every sense. Test did not mine rules, choose K, or adjust thresholds. See [EDA figures and interpretation](../docs/eda_report.md).

## 4. Association rules and algorithm comparison

Each invoice is a binary StockCode set; Quantity cannot count an item multiple times. Every basket remains in the support denominator, including single-item baskets. The 3,564-product vocabulary uses train only.

For A→B: support=count(A∪B)/N; confidence=count(A∪B)/count(A); lift=confidence/(count(B)/N). Python bitsets independently verify counts. Mine presence only, aligning Weka thresholds because Apriori rounds support×N while FP-Growth uses ceil.

Weka 3.8.7 is the actual backend. Full-train FP-Growth completes support 1%, 2%, 5%; Apriori reaches the 45-second wall limit at 1%/2% and completes at 5% with zero rules. Partial outputs and timeout durations are not treated as completed runs. A matched 500-training-invoice comparison produces 800 rules at 2% and four at 5%, identical across algorithms in every count. Three repetitions report medians. Timings combine fitting/rule generation; separate mining time and memory were not measured.

The 18 settings combine support 1/2/5%, reported length 2/3, confidence 0.3/0.5/0.7, lift≥1.1, count≥20. Validation selects support 1%, length 2, confidence≥0.3: 738 rules. Support requires at least 111 of 11,044 training baskets.

| Rule, training display names | Train count | Train confidence | Train lift | Test count | Test confidence | Test lift |
|---|---:|---:|---:|---:|---:|---:|
| JUMBO BAG PINK POLKADOT → JUMBO BAG RED RETROSPOT | 509 | 68.41% | 6.27 | 164 | 67.77% | 7.72 |
| GREEN REGENCY TEACUP AND SAUCER → ROSES REGENCY TEACUP AND SAUCER | 483 | 74.88% | 12.44 | 157 | 77.72% | 19.42 |
| JUMBO STORAGE BAG SUKI → JUMBO BAG RED RETROSPOT | 440 | 59.38% | 5.44 | 150 | 64.38% | 7.34 |
| JUMBO SHOPPER VINTAGE RED PAISLEY → JUMBO BAG RED RETROSPOT | 421 | 59.55% | 5.46 | 142 | 55.25% | 6.30 |
| LUNCH BAG SUKI DESIGN → LUNCH BAG RED RETROSPOT | 378 | 49.93% | 5.93 | 137 | 52.09% | 9.04 |

Jumbo-bag and teacup rules suggest within-category cross-selling hypotheses. They establish co-occurrence, not causality. High lift alone is insufficient; count, confidence, and later-period evidence remain visible.

## 5. RFM and K-means

R is calendar days since the last purchase at cutoff 2011-08-01; F is distinct valid invoices; M is gross purchases. Apply log1p and training-population mean/std scaling. K-means uses all three features with Euclidean distance and Weka internal normalization disabled.

Test K=2–8 with five seed groups 42–46 and 20 K-means++ starts per group, maximum 300 iterations; retain the lowest-SSE solution per group. Total: 700 starts. Euclidean silhouette uses all 3,145 customers; independently check SSE, pairwise ARI, and smallest cluster sizes. Eligible K requires mean ARI≥0.8 and each cluster≥3%; maximize mean silhouette, preferring smaller K within 0.005. K=2 gives mean silhouette 0.4440 and mean ARI 0.9954.

| Segment | Training customers | Median R, days | Median F, invoices | Median M, GBP | Gross training-purchase share |
|---|---:|---:|---:|---:|---:|
| Segment_1 | 1,048 | 19 | 5 | 1,639.80 | 79.90% |
| Segment_2 | 2,097 | 102 | 1 | 315.00 | 20.10% |

![Original-unit segment profiles](../results/figures/10_segment_profiles.png)

Segment_1 is more recent, frequent, and higher in gross purchases; Segment_2 is less active within the training window. These are not verified churn/profitability labels. PCA is a display projection only; clustering uses all three features, and silhouette is not accuracy against true customer labels.

## 6. Offline evaluation and results

This is basket completion, not click-order prediction. Hide one item per eligible basket using a fixed hash, exclude observed items, and fill top five from training popularity. Retain targets outside the training vocabulary. Methods share baskets, targets, and fallback within each comparison cohort.

Validation global HitRate@5 is 13.76% versus popularity 2.79%; validation selects settings. After hashing/freeze and without refitting, final test gives:

| Method | Hits/baskets | HitRate@5 | 95% CI | Precision@5 | Rule coverage |
|---|---:|---:|---:|---:|---:|
| Global rules, all train | 458/5183 | 8.84% | [8.03%; 9.66%] | 1.77% | 81.25% |
| Popularity | 90/5183 | 1.74% | [1.38%; 2.11%] | 0.35% | 0.00% |

Same-cohort comparison on 3,579 eligible training-profile customer baskets:

| Method | Hits/baskets | HitRate@5 | 95% CI | Precision@5 | Rule coverage |
|---|---:|---:|---:|---:|---:|
| Global rules, identified train | 315/3579 | 8.80% | [7.77%; 9.83%] | 1.76% | 71.92% |
| Popularity | 78/3579 | 2.18% | [1.68%; 2.71%] | 0.44% | 0.00% |
| Segment rules | 317/3579 | 8.86% | [7.90%; 9.89%] | 1.77% | 71.61% |

The all-training and identified-training models/popularity use different training cohorts; compare methods within each table.

![Final-test comparison](../results/figures/16_final_test_comparison.png)

Paired 2,000-replicate CustomerID bootstrap gives global−popularity **+7.10 percentage points**, 95% CI **[+6.34; +7.89]**. Segment−identified-global is **+0.056 percentage points**, CI **[−0.475; +0.600]**: no demonstrated improvement from segmentation. Missing-ID invoices are separate units. Intervals condition on fixed models/period and have no multiple-comparison adjustment.

With one hidden target, Recall@5 equals HitRate@5. Precision@5 uses five fixed recommendation positions per basket; all methods return five here. Rule coverage measures any rule-based recommendation, not absence of partial popularity filling.

## 7. Research answers and applications

- **RQ1:** Global rules have co-occurrence evidence and outperform popularity on masked-basket test. Of 738 fixed rules, 689 have test joint count≥20 and 720 test lift>1. These describe stability, not independent significance tests per rule.
- **RQ2:** Two RFM groups are stable across seeds and interpretable in original behavior. They describe purchasing activity, not verified churn or profitability.
- **RQ3:** Partitioning customers does not guarantee better recommendations. Segment validation is lower than global; the small test difference has an interval containing zero. There is insufficient evidence that segment rules improve performance.

High-evidence rules could inform cross-sell placements for bags/teacups, while RFM describes experimental audiences. A customer-level A/B test with predefined outcomes is needed to measure live effects. Specific discounts are unsupported without margins/costs.

## 8. Limitations and future work

The data describe one historical retailer concentrated in the UK and do not automatically generalize to Vietnam. Gross Monetary includes purchases later reversed; duplicate handling is an assumption. Missing-ID customers cannot be followed reliably, and masked items do not reproduce real interactions. Test has 743/5,183 unseen targets (14.33%) versus validation 6.39%; train-only candidates cannot recommend them. Changes in period/product mix and validation selection may contribute to the performance decline; causes are not established.

Transformation/outlier ablations, a second clustering method, memory benchmarking, and separate mining/generation timing remain undone. Future work should evaluate periodic retraining on a new period, return-policy sensitivity, and practical utility in live experiments. Do not tune on this used test and call a repeat evaluation independent.

## 9. Reproducibility, checks, and submission status

Actual environment: Python 3.12.14; Weka 3.8.7; openjdk version "25.0.4" 2026-07-21 LTS; pandas 3.0.1; NumPy 2.3.5; ReportLab 4.4.9. Python versions are recorded in requirements-experiments-python.lock.txt; Weka/environment hashes in results/tables/model_environment.json.

All 24 tests pass. Raw/prepared hashes are unchanged, rule counts independently checked, cohorts matched, and source/model/evaluator hashes frozen before test. [README](../README.md) explains execution. The training runner stops after freezing; [final runner](../scripts/run_final_evaluation.ps1) verifies saved results and retains the English reports without rescoring.

Historical training/validation snapshots keep test=false. Current state is configs/project.json and results/tables/final_test/evaluation_receipt.json. Rubric/team details, report formatting, slides, and submission confirmation remain pending; the project is not yet submitted or defended.

## References and evidence

- Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33. CC BY 4.0.
- Chen, D., Sain, S. L., & Guo, K. (2012). *Data mining for the online retail industry: A case study of RFM model-based customer segmentation using data mining*. Journal of Database Marketing & Customer Strategy Management, 19, 197–208. https://doi.org/10.1057/dbm.2012.17. Reading notes: [literature_notes.md](../docs/literature_notes.md).
- Weka SimpleKMeans: https://weka.sourceforge.io/doc.stable/weka/clusterers/SimpleKMeans.html.
- Weka FP-Growth: https://weka.sourceforge.io/doc.stable/weka/associations/FPGrowth.html.
- [Training/validation report](../docs/experiment_report.md); [final-test report](../docs/final_evaluation_report.md).
- [Final protocol](../configs/final_evaluation_protocol.json); [freeze lock](../results/models/final_evaluation_lock.json); [receipt](../results/tables/final_test/evaluation_receipt.json).
