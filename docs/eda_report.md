# EDA — purchasing behavior and RFM

Data follow policy 1.0. Full-period plots describe history; test-model results do not select parameters. RFM, popular-product rankings, and correlations use train only.

## 1. Scale, time, and invoice value

![Figure 1. Monthly invoice counts and merchandise purchases before returns.](../results/figures/01_monthly_purchases.png)

December 2011 ends on December 9; do not compare its total as a complete month. Amounts are neither profit nor net revenue.

| Cohort | Invoices | Median GBP | P95 GBP | P99 GBP | Max GBP |
|---|---:|---:|---:|---:|---:|
| all_periods | 19,773 | 302.20 | 1,508.07 | 4,408.93 | 168,469.60 |
| train | 11,044 | 295.48 | 1,409.24 | 3,780.75 | 77,183.60 |

![Figure 2. Log1p invoice-value distribution, retaining the complete tail.](../results/figures/14_invoice_value_distribution.png)

Large values/quantities warrant review but do not prove wholesale status. Large-purchase return counterparts are documented in preparation.

## 2. Baskets, products, and countries

![Figure 3. Distinct products per basket; single-item baskets remain in support denominators.](../results/figures/03_basket_size_distribution.png)

![Figure 4. Products appearing in the most training invoices; popularity is not total Quantity.](../results/figures/02_train_top_products.png)

| StockCode | Training display name | Training invoices | Invoice prevalence |
|---|---|---:|---:|
| 85123A | WHITE HANGING HEART T-LIGHT HOLDER | 1,411 | 12.78% |
| 22423 | REGENCY CAKESTAND 3 TIER | 1,272 | 11.52% |
| 85099B | JUMBO BAG RED RETROSPOT | 1,205 | 10.91% |
| 47566 | PARTY BUNTING | 1,173 | 10.62% |
| 20725 | LUNCH BAG RED RETROSPOT | 930 | 8.42% |

![Figure 5. Invoice concentration by country.](../results/figures/04_country_concentration.png)

The United Kingdom accounts for 90.53% of valid merchandise invoices. Every country is retained, but this market dominates; results do not automatically generalize to Vietnamese e-commerce.

## 3. Training RFM and purchase-value concentration

![Figure 6. Original and log1p RFM for the same 3,145 training customers.](../results/figures/05_train_rfm_distributions.png)

Original skewness: Recency 0.814, Frequency 9.018, Monetary 15.349. Frequency/Monetary are strongly right-skewed. Log1p/standardization reduces scale dominance but does not replace checking transaction meaning.

![Figure 7. Gross purchase-value concentration among training customers.](../results/figures/06_train_purchase_concentration.png)

The top 10% of training customers contribute about 58.97% of merchandise purchases before returns. This describes gross purchases, not profit distribution.

![Figure 8. Correlations between training log-z features.](../results/figures/07_train_rfm_correlations.png)

Frequency and Monetary both partly reflect purchasing activity. Correlation does not establish causality. RFM has no verified churn labels; high Recency does not prove churn.

## 4. Implications for experiments

- Rules use invoice presence and every basket in the denominator; large Quantity does not repeatedly increase support.
- K-means uses three training-fitted log-z features; K requires separation, stability, size, and interpretability.
- Split chronologically and keep entire invoices together; vocabulary/names use train only.
- Report new/missing-ID customers and new products; do not remove difficult cases to inflate metrics.

Source tables are in results/tables/eda. Figures are available as PNG and SVG for reports/slides.
