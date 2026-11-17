# Final-test evaluation with frozen models

## 1. Configuration and evaluation policy

Test invoices run from 2011-10-01 through 2011-12-09. Retain the training-fitted 738 global rules, 455 identified-cohort global rules, 574/230 rules for the two segments, and K-means K=2. No validation/test refitting and no support/confidence/K changes after observing test results.

The additional protocol was saved before scoring in configs/final_evaluation_protocol.json. Data, rules, model, scaler, and evaluator hashes were frozen in results/models/final_evaluation_lock.json. The receipt records execution time and output hashes. Subsequent calls verify saved results without rescoring.

Hide one item in each basket containing at least two distinct products, using the same invoice hash/seed 42 as validation. Unseen targets remain in the denominator. Candidates/ranking use train only; observed products are excluded and training popularity fills up to five recommendations.

The all-basket comparison uses all-training popularity for both global rules and baseline. The segment comparison uses the same training-profile customer cohort and identified-training popularity for all three methods. Identical method names across different training/cohort scopes must not be directly compared.

## 2. Cohorts and new products

| Cohort | All baskets | Eligible | Single-item | Identified customers | Targets unseen in train |
|---|---:|---:|---:|---:|---:|
| all_baskets | 5,572 | 5,183 | 389 | 2,559 | 743 |
| missing_customer_id | 251 | 222 | 29 | 0 | 38 |
| new_identified_customers | 1,468 | 1,382 | 86 | 929 | 184 |
| train_profile_customers | 3,853 | 3,579 | 274 | 1,630 | 521 |

The 389 single-item baskets are ineligible for masking but remain in test rule-support denominators. New/missing-ID customers receive no invented segment. Cohort customer counts include all customers; bootstrap uses only those with eligible baskets.

## 3. All-basket results

| Method | Hits/baskets | HitRate@5 | 95% CI | Precision@5 | Rule coverage |
|---|---:|---:|---:|---:|---:|
| Global rules (all train) | 458/5183 | 8.84% | [8.03%; 9.66%] | 1.77% | 81.25% |
| Popularity | 90/5183 | 1.74% | [1.38%; 2.11%] | 0.35% | 0.00% |

Global improves by **7.10 percentage points**, paired bootstrap 95% CI **[+6.34; +7.89] percentage points**. This is evidence for offline masked-basket completion in this period, not revenue gains or live deployment effectiveness.

## 4. Global and segment rules on the same cohort

| Method | Hits/baskets | HitRate@5 | 95% CI | Precision@5 | Rule coverage |
|---|---:|---:|---:|---:|---:|
| Global rules (identified train) | 315/3579 | 8.80% | [7.77%; 9.83%] | 1.76% | 71.92% |
| Popularity | 78/3579 | 2.18% | [1.68%; 2.71%] | 0.44% | 0.00% |
| Segment rules | 317/3579 | 8.86% | [7.90%; 9.89%] | 1.77% | 71.61% |

Segment rules add exactly two hits: 317 versus 315 among 3,579 baskets. Difference: **+0.056 percentage points**, 95% CI **[−0.475; +0.600] percentage points**. The interval includes zero: insufficient evidence of improvement, not proof of equivalence.

![Final-test results and confidence intervals](../results/figures/16_final_test_comparison.png)

## 5. Metrics and uncertainty

- HitRate@5 = baskets whose target appears in the top five / eligible baskets. With one hidden target, Recall@5 has the same value.
- Precision@5 uses a fixed denominator: hits/(5 × eligible baskets). Unfilled positions count in the denominator. Every method returned five items in this run.
- Rule coverage is the fraction with at least one rule-based recommendation. Zero-rule fallback is its complement; even covered baskets may need popularity to fill remaining positions.
- Paired bootstrap: 2,000 resamples, seed 20261118, resample CustomerIDs and retain all their baskets. Use the same resample for compared methods; rates remain basket-weighted. Missing-ID invoices are separate units.
- Intervals are percentile 2.5%–97.5%, conditional on fixed models/period; they exclude retraining uncertainty, have no multiple-comparison adjustment, and do not replace A/B tests. Independent missing-ID invoices are an approximation.

## 6. Customer-group and segment breakdown

| Cohort | Method | Eligible baskets | HitRate@5 | Rule coverage |
|---|---|---:|---:|---:|
| all_model/missing_customer_id | Global rules | 222 | 8.11% | 74.77% |
| all_model/missing_customer_id | Popularity | 222 | 1.80% | 0.00% |
| all_model/new_identified_customers | Global rules | 1,382 | 7.45% | 83.00% |
| all_model/new_identified_customers | Popularity | 1,382 | 1.30% | 0.00% |
| all_model/train_profile_customers | Global rules | 3,579 | 9.42% | 80.97% |
| all_model/train_profile_customers | Popularity | 3,579 | 1.90% | 0.00% |
| segment/Segment_1 | Global identified rules | 2,375 | 9.05% | 72.88% |
| segment/Segment_1 | Popularity | 2,375 | 2.06% | 0.00% |
| segment/Segment_1 | Segment rules | 2,375 | 9.81% | 74.32% |
| segment/Segment_2 | Global identified rules | 1,204 | 8.31% | 70.02% |
| segment/Segment_2 | Popularity | 1,204 | 2.41% | 0.00% |
| segment/Segment_2 | Segment rules | 1,204 | 6.98% | 66.28% |

Segment breakdowns are descriptive, without separate CIs/multiplicity adjustment. Do not use them to reselect K or choose a method for each segment on this same test. all_model rows use the 738-rule all-training model; identified comparisons use the 455-rule identified-cohort model and different popularity.

## 7. Stability of fixed rules

| Group | Fixed rules | Test baskets for support | Antecedent absent | Joint count <20 | Joint count ≥20 | Test lift >1 |
|---|---:|---:|---:|---:|---:|---:|
| selected_global | 738 | 5572 | 13 | 49 | 689 | 720 |
| global_identified | 455 | 3853 | 0 | 76 | 379 | 455 |
| Segment_1 | 574 | 2579 | 1 | 195 | 379 | 572 |
| Segment_2 | 230 | 1274 | 0 | 180 | 50 | 229 |

Count 20 is a descriptive evidence flag, not a significance test. Undefined confidence/lift are blank when denominators are zero. No test-based rule filtering and rescoring took place.

## 8. Validation versus test

Global HitRate@5 declines from 13.76% on validation to 8.84% on test. Unseen-target share rises from 188/2,944 = 6.39% to 743/5,183 = 14.33%. Train-only candidates cannot hit these targets. Changes in product/time composition and validation-selection optimism are possible explanations, not established causes.

Errors are selected by InvoiceNo order rather than favorable narratives; see [error_examples.csv](../results/tables/final_test/error_examples.csv). Monthly retraining has not been evaluated; it requires a new evaluation period.

## 9. Verification and outputs

- [case_predictions.csv.gz](../results/tables/final_test/case_predictions.csv.gz) records targets, recommendations, hits, and bootstrap units.
- [evaluation_receipt.json](../results/tables/final_test/evaluation_receipt.json) and [final_evaluation_lock.json](../results/models/final_evaluation_lock.json) document the pre-scoring freeze.
- [Protocol](../configs/final_evaluation_protocol.json); metric/cohort/rule/CI tables are under results/tables/final_test.
- Run `& .\scripts\run_final_evaluation.ps1` to verify saved results and retain the English reports/render the final figure; a saved receipt prevents rescoring.

Remaining work: check the rubric, format the submission, prepare slides/defense, and validate the package. Submission and instructor/team/deadline confirmations are pending. The test has been used; further model selection on it is not an independent evaluation.
