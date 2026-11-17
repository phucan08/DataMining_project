# Project Proposal — Draft v0.1

**Topic:** Mining E-commerce Purchasing Behavior Using Association Rules and Customer Segmentation  
**Status:** draft for review/registration; instructor approval has not been confirmed.  
**Team, deadline, and report template:** not provided; see [course_requirements.md](course_requirements.md).

This document records the proposed study. Current findings are in [project_report.md](../report/project_report.md).

## 1. Background and problem

Transaction histories help retailers understand purchases and differences between customer groups. Bestseller statistics alone do not explain which products are purchased together or how these patterns vary by segment.

The project builds a pipeline from transactions to association rules and customer segments, then compares global and segment-specific rules. Intended users are sales/marketing analysts. Results support hypotheses about bundles and cross-selling that require subsequent validation.

## 2. Objectives and research questions

- **RQ1:** Which co-purchase rules have sufficient evidence, practical meaning, and support in a later period?
- **RQ2:** Which segments do RFM and K-means produce, how separated/stable are they, and can purchasing behavior explain them?
- **RQ3:** How do segment-specific and global rules differ on compatible eligible customer cohorts?

The objective is interpretable, reproducible findings. No required cluster/rule count or minimum improvement is predetermined.

## 3. Dataset and units of analysis

Use **UCI Online Retail**, ID 352, licensed CC BY 4.0 [1]. Raw audit confirmed 541,909 rows, eight columns, and timestamps from 2010-12-01 08:26 to 2011-12-09 12:50. CustomerID is missing on 135,080 rows and Description on 1,454; see [raw audit](raw_audit_report.md). These are raw counts, not valid purchases after cleaning.

- Basket: one invoice containing its set of StockCode values.
- Customer: one CustomerID summarized as Recency, Frequency, Monetary.
- Product key: StockCode; Description is a display name only.
- Country scope: retain every country; separately report identified customers eligible for RFM.

Segmentation requires a valid CustomerID. Missing-ID transactions are considered separately for global rules, never assigned an invented customer.

## 4. Proposed methods

1. **Audit/preprocessing:** inspect types, missingness, cancellations/returns, invalid prices/quantities, service codes, and duplicates; log each step. Do not remove wholesale customers solely for high spending.
2. **EDA:** summarize transactions, basket sizes, popular products, and purchase values; distinguish complete and partial months.
3. **Rules:** build binary invoice–item data; compare Apriori/FP-Growth with identical inputs, support thresholds, and comparable length settings; examine support, confidence, lift, and supporting counts [3].
4. **Segmentation:** calculate RFM at a fixed cutoff; inspect outliers, transform appropriately, standardize before K-means. Study [2] is background; implementation is designed/tested separately.
5. **Segment mining:** join invoices to segments; compare group rules with global rules on the same eligible identified cohort.

Adopted RFM uses calendar-day Recency, distinct valid purchase invoices for Frequency, and valid merchandise purchases **before returns** for Monetary, not net revenue. Policy 1.0 and evidence are in [data_preparation_policy.md](data_preparation_policy.md). Preparation produced 522,537 purchase lines, 19,773 baskets, and 3,145 training profiles. Later experiment reports contain model results.

## 5. Experimental design and evaluation

- Chronological discovery/train before 2011-08-01; validation from 2011-08-01 to before 2011-10-01; final test from 2011-10-01 to before 2011-12-10. Assign each entire invoice using its last source-line timestamp.
- Learn vocabulary, transformations, scaler, RFM, and clusters from train; select configurations using validation. Freeze before final test.
- Keep cutoff-time models/profiles for later comparisons. Report new customers separately; do not construct historical profiles using future transactions.
- **Rules:** compare itemsets, measure runtime under matched conditions, recompute held-out counts/support/confidence/lift of fixed rules. Zero denominators are undefined.
- **Clusters:** assess silhouette, inertia/elbow, size, seed stability, and original-unit RFM. No accuracy without ground-truth labels.
- **Integration:** compare compatible cohorts; discuss small groups and rare high-lift rules.

An optional recommendation extension compares offline basket completion with train-popularity, global-rule, and segment-rule baselines. Only such evaluation supports recommendation-metric claims; it does not establish increased revenue.

## 6. Scope, deliverables, limitations

**Core:** data/cleaning audit; EDA; Apriori–FP-Growth benchmark; rules; segment profiles; global–segment comparison; code/config/README; report/slides.

**Extensions:** offline recommendation evaluation, a second clustering algorithm, a small demo. Interface scope depends on the rubric.

Limitations include one retailer, a finite historical period, seasonality, wholesale behavior, missing customers, cold start, and no cost/profit data or live sales experiment. Rules capture co-occurrence, not causality or purchase order.

## 7. Illustrative schedule and responsibilities

| Week from start | Work | Checkpoint |
|---|---|---|
| 1 | Proposal, environment, data, audit, EDA, protocol | Verified source and explicit handling policy |
| 2 | Baskets, global rules, RFM, K-means | Interpretable rules and profiles |
| 3 | Segment rules, validation, freeze, final evaluation | Results addressing all RQs |
| 4 | Reproduction, report, slides, required demo, defense rehearsal | Reproducible submission |

This is a sample schedule, not an official deadline. Members are unknown, so roles remain unassigned: data, rules, segmentation, integration/verification/reporting. One person may cover multiple roles.

## References

1. Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33. Dataset: https://archive.ics.uci.edu/dataset/352/online+retail.
2. Chen, D., Sain, S. L., & Guo, K. (2012). *Data mining for the online retail industry: A case study of RFM model-based customer segmentation using data mining*. Journal of Database Marketing & Customer Strategy Management, 19, 197–208. https://doi.org/10.1057/dbm.2012.17.
3. mlxtend. *Association rules*. https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/.
4. scikit-learn. *KMeans*. https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html.
