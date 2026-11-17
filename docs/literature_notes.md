# Background literature notes

## 1. RFM/customer segmentation — original study

**Chen, D., Sain, S. L., & Guo, K. (2012).** *Data mining for the online retail industry: A case study of RFM model-based customer segmentation using data mining*. DOI: https://doi.org/10.1057/dbm.2012.17.

The preprocessing, clustering, and conclusion sections were read from the author manuscript in the LSBU repository. The study uses RFM, K-means, and decision trees, emphasizing preparation, differences in scale, and cluster interpretation. Its data include PostCode and address fields, unlike the selected UCI schema. Mining joint purchases within customer groups is discussed as future work. Do not present the study's cluster counts or findings as this project's results.

Full source: https://openresearch.lsbu.ac.uk/download/a7d91f552531769d0e73e3add16f49ee8f0e357e79c994f202314fbc779cb301/356215/dbm201217a%20Data%20mining%20for%20the%20online%20retail%20industry%20-%20A%20case%20study%20of%20RFM%20model-based%20customer%20segmentation%20using%20data%20mining.pdf

## 2. Association rules — official documentation

Source: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/.

Definitions were reviewed for disjoint itemsets A and B and N baskets:

- support(A → B) = count(A ∪ B) / N.
- confidence(A → B) = count(A ∪ B) / count(A), when count(A) > 0.
- lift(A → B) = confidence(A → B) / support(B), when support(B) > 0.

## 3. Project design decisions

The proposal called for CustomerID-based RFM, immutable raw data, identical inputs for algorithm comparisons, later-period rule evaluation, interpretation in original RFM units, and no future transactions in historical cluster assignments. These are project design choices, not findings from the cited sources. Their implementation is documented in [experiment_report.md](experiment_report.md) and [final_evaluation_report.md](final_evaluation_report.md); course-specific approval remains pending.
