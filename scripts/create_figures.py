"""Create EDA and experiment figures with their exact numeric source tables."""
from __future__ import annotations
import json,sys
from pathlib import Path
import numpy as np,pandas as pd
from reportlab.graphics.shapes import String,Rect
from reportlab.lib import colors
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.plotting import figure,note,bars,lines,save,PALETTE

def main():
    figures=ROOT/'results/figures';tables=ROOT/'results/tables/eda';tables.mkdir(parents=True,exist_ok=True)
    baskets=pd.read_csv(ROOT/'data/processed/baskets.csv',dtype={'InvoiceNo':'string','CustomerID':'string'},parse_dates=['InvoiceTimestamp'])
    rfm=pd.read_csv(ROOT/'data/processed/rfm_train.csv',dtype={'CustomerID':'string'})
    features=pd.read_csv(ROOT/'data/processed/rfm_train_features.csv',dtype={'CustomerID':'string'})
    monthly=baskets.assign(month=baskets['InvoiceTimestamp'].dt.strftime('%Y-%m')).groupby('month').agg(invoices=('InvoiceNo','size'),gross_purchase_micro_gbp=('PurchaseValueMicroGBP','sum')).reset_index()
    monthly['gross_purchase_gbp']=monthly['gross_purchase_micro_gbp']/1e6;monthly['partial_month']=monthly['month'].eq('2011-12')
    monthly.to_csv(tables/'monthly_purchases.csv',index=False)
    d=figure('Monthly merchandise purchasing','All periods, descriptive only. December 2011 contains data through December 9.')
    bars(d,monthly['invoices'].tolist(),monthly['month'].tolist(),90,350,930,170,'Valid merchandise invoices',rotate=35)
    bars(d,(monthly['gross_purchase_gbp']/1e6).tolist(),monthly['month'].tolist(),90,95,930,160,'Gross merchandise purchase value (million GBP)',rotate=35)
    note(d,'Purchases before returns; fees/vouchers excluded. Full-period EDA does not select model parameters.');save(d,figures/'01_monthly_purchases.svg')

    catalog=pd.read_csv(ROOT/'data/processed/product_catalog_train.csv',dtype={'StockCode':'string'})
    with np.load(ROOT/'data/processed/basket_train_coordinates.npz') as matrix:
        counts=np.bincount(matrix['column_indices'],minlength=int(matrix['shape'][1]));n=int(matrix['shape'][0])
    products=catalog.assign(invoice_count=counts,invoice_prevalence=counts/n).sort_values('invoice_count',ascending=False)
    products.to_csv(tables/'train_product_popularity.csv',index=False)
    top=products.head(10).iloc[::-1]
    labels=[f"{row.StockCode}  {str(row.DisplayName)[:35]}" for row in top.itertuples()]
    d=figure('Products appearing in the most train baskets','Frequency is the number of distinct invoices, not units sold.')
    bars(d,top['invoice_count'].tolist(),labels,390,100,620,420,horizontal=True)
    note(d,'Train only: 11,044 baskets. Product labels use the train catalog.');save(d,figures/'02_train_top_products.svg')

    ranges=[(1,1),(2,2),(3,5),(6,10),(11,20),(21,50),(51,100),(101,np.inf)]
    distribution=pd.DataFrame([{'range':str(a) if a==b else f'{a}–{int(b)}' if np.isfinite(b) else '101+', 'baskets':int(baskets['UniqueProducts'].between(a,b).sum())} for a,b in ranges])
    distribution.to_csv(tables/'basket_size_distribution.csv',index=False)
    d=figure('Basket size distribution','All valid merchandise baskets; single-item baskets remain in the support denominator.')
    bars(d,distribution['baskets'].tolist(),distribution['range'].tolist(),100,120,900,370,'Distinct products per invoice')
    note(d,f"All {len(baskets):,} baskets included; no tail clipping.");save(d,figures/'03_basket_size_distribution.svg')

    country=baskets.groupby('Country').agg(invoices=('InvoiceNo','size'),gross_micro_gbp=('PurchaseValueMicroGBP','sum'),identified_customers=('CustomerID','nunique')).sort_values('invoices',ascending=False).reset_index()
    country['invoice_fraction']=country['invoices']/len(baskets);country.to_csv(tables/'country_purchases.csv',index=False)
    top=country.head(10).iloc[::-1]
    d=figure('Geographical concentration','All countries retained; raw country labels are not customer segments.')
    bars(d,(top['invoice_fraction']*100).tolist(),top['Country'].tolist(),220,110,790,400,'Share of valid merchandise invoices (%)',horizontal=True)
    note(d,'Customer counts by country must not be added if a customer appears in multiple countries.');save(d,figures/'04_country_concentration.svg')

    d=figure('Invoice gross purchase value distribution','Log1p display preserves every invoice, including extreme values; no value-based filtering.')
    invoice_summaries=[]
    for position,split in enumerate(['all_periods','train']):
        sample=baskets if split=='all_periods' else baskets.loc[baskets['Split'].eq('train')]
        values=sample['PurchaseValueGBP'].to_numpy();frequencies,edges=np.histogram(np.log1p(values),bins=25)
        labels=[f'{edges[i]:.1f}' if i%5==0 else '' for i in range(25)]
        bars(d,frequencies.tolist(),labels,90+position*520,170,420,310,split+'; x = log1p(GBP)',rotate=20)
        invoice_summaries.append({'cohort':split,'invoices':len(values),'median_gbp':float(np.median(values)),'p95_gbp':float(np.quantile(values,.95)),'p99_gbp':float(np.quantile(values,.99)),'max_gbp':float(values.max()),'median_quantity':float(sample['TotalQuantity'].median()),'max_quantity':int(sample['TotalQuantity'].max())})
    pd.DataFrame(invoice_summaries).to_csv(tables/'invoice_value_summary.csv',index=False)
    note(d,'Values are merchandise purchases before returns; very large orders alone do not prove wholesale status.');save(d,figures/'14_invoice_value_distribution.svg')

    d=figure('Train RFM distributions: original and log1p','Full observed ranges are displayed; no customers or extreme transactions are removed.',width=1280,height=900)
    histograms=[]
    for column_index,column in enumerate(['Recency','Frequency','Monetary']):
        for row_index,transform in enumerate(['raw','log1p']):
            values=rfm[column].to_numpy(dtype=float);values=values if transform=='raw' else np.log1p(values)
            frequencies,edges=np.histogram(values,bins=20)
            labels=[f'{edges[i]:.1f}' if i%5==0 else '' for i in range(20)]
            bars(d,frequencies.tolist(),labels,80+column_index*410,480-row_index*370,325,245,f'{column} — {transform}',rotate=20)
            histograms.extend({'variable':column,'transform':transform,'left':edges[i],'right':edges[i+1],'customers':int(frequencies[i])} for i in range(20))
    pd.DataFrame(histograms).to_csv(tables/'rfm_histograms.csv',index=False)
    note(d,'Train profiles only, cutoff 2011-08-01. Monetary is gross purchases before returns.');save(d,figures/'05_train_rfm_distributions.svg')

    monetary=np.sort(rfm['Monetary'].to_numpy());x=np.arange(len(monetary)+1)/len(monetary);y=np.r_[0,np.cumsum(monetary)/monetary.sum()]
    concentration=pd.DataFrame({'customer_fraction':x,'purchase_value_fraction':y});concentration.to_csv(tables/'train_purchase_concentration.csv',index=False)
    top_share=float(np.sort(monetary)[-int(np.ceil(.1*len(monetary))):].sum()/monetary.sum())
    d=figure('Gross purchase concentration among train customers',f'Top 10% of customers account for {100*top_share:.1f}% of train gross purchase value.')
    chart=lines(d,[list(zip(x[::10],y[::10]))+[(1.,1.)],[(0.,0.),(1.,1.)]],100,100,900,400,'Cumulative customer share (x) vs purchase-value share (y)',labels=['Observed concentration','Equal share'])
    chart.xValueAxis.valueMin=0;chart.xValueAxis.valueMax=1;chart.yValueAxis.valueMin=0;chart.yValueAxis.valueMax=1
    note(d,'Gross purchase value excludes fees and is not profit or spend net of returns.');save(d,figures/'06_train_purchase_concentration.svg')

    correlation=features.iloc[:,1:].corr();correlation.to_csv(tables/'train_rfm_feature_correlation.csv')
    d=figure('Correlation between train log-standardized RFM features','Pearson correlation; association does not imply causation.')
    names=['Recency','Frequency','Monetary'];size=115
    for i in range(3):
        d.add(String(390+i*size,490,names[i],fontSize=12,textAnchor='middle'))
        d.add(String(300,415-i*size,names[i],fontSize=12,textAnchor='end'))
        for j in range(3):
            value=float(correlation.iloc[i,j]);intensity=abs(value)
            color=colors.Color(1-.7*intensity,1-.8*intensity,1-.2*intensity) if value<0 else colors.Color(1-.1*intensity,1-.75*intensity,1-.75*intensity)
            d.add(Rect(335+j*size,355-i*size,size,size,fillColor=color,strokeColor=colors.white))
            d.add(String(390+j*size,405-i*size,f'{value:.2f}',fontName='Helvetica-Bold',fontSize=17,textAnchor='middle'))
    note(d,'Computed on the same 3,145 train customers used for clustering.');save(d,figures/'07_train_rfm_correlations.svg')

    models=ROOT/'results/tables/models'
    if (models/'clustering_k_comparison.csv').exists():
        selection=pd.read_csv(models/'clustering_k_comparison.csv')
        d=figure('Choosing K: compactness, separation and stability','Each K uses five seed groups, with 20 K-means++ starts per group; train data only.')
        lines(d,[list(zip(selection['k'],selection['mean_sse']))],90,150,420,340,'Mean within-cluster SSE')
        lines(d,[list(zip(selection['k'],selection['mean_silhouette']))],650,150,350,340,'Mean full-train silhouette')
        note(d,'K eligibility also requires minimum cluster size and mean pairwise adjusted Rand index.');save(d,figures/'08_k_selection.svg')
        assignments=pd.read_csv(models/'cluster_assignments_train.csv',dtype={'CustomerID':'string'})
        values=features.iloc[:,1:].to_numpy();_,singular,components=np.linalg.svd(values-values.mean(axis=0),full_matrices=False)
        projected=values@components[:2].T;ratio=singular**2/(singular**2).sum()
        projection=pd.DataFrame({'CustomerID':features['CustomerID'],'PC1':projected[:,0],'PC2':projected[:,1],'Segment':assignments['Segment']})
        projection.to_csv(tables/'train_cluster_pca_projection.csv',index=False)
        (tables/'pca_display_metadata.json').write_text(json.dumps({'explained_variance_ratio':ratio.tolist(),'components':components.tolist(),'display_only_not_clustering_features':True},indent=2)+'\n')
        d=figure('Train customer segments: two-dimensional PCA view',f'PC1 {100*ratio[0]:.1f}% and PC2 {100*ratio[1]:.1f}% variance; clustering uses all three log-z features.')
        groups=sorted(projection['Segment'].unique());points=[list(projection.loc[projection['Segment'].eq(name),['PC1','PC2']].itertuples(index=False,name=None)) for name in groups]
        lines(d,points,100,100,900,390,'PC1 (x) and PC2 (y)',labels=groups,scatter=True)
        note(d,'This projection can hide separation in the third dimension; it is not a cluster quality metric.');save(d,figures/'09_train_cluster_projection.svg')
        profiles=pd.read_csv(models/'cluster_profiles.csv')
        d=figure('Customer segment profiles in original RFM units','Medians from actual train customers; segment names describe gross purchasing, not profitability.')
        for i,(column,title) in enumerate([('median_recency','Median recency (days)'),('median_frequency','Median invoice count'),('median_monetary','Median gross purchase value (GBP)')]):
            bars(d,profiles[column].tolist(),profiles['Segment'].tolist(),80+i*355,170,270,280,title,rotate=25)
        note(d,'Raw medians aid interpretation; K-means was fitted to log1p and standardized values.');save(d,figures/'10_segment_profiles.svg')
    benchmark=pd.read_csv(ROOT/'results/experiments/global_rules/benchmark_status.csv')
    complete=benchmark.loc[benchmark['status'].eq('completed')]
    table=complete.groupby(['algorithm','requested_support'])['fit_and_rule_generation_ms'].agg(['median','min','max']).reset_index()
    table.to_csv(tables/'rule_runtime_summary.csv',index=False)
    d=figure('Weka association-rule runtime: completed full-train fits','45-second wall limit per attempt. Apriori timeouts at 1% / 2% are not plotted as successful fits.')
    labels=[];values=[]
    for row in table.itertuples():labels.append(f'{row.algorithm}, support {100*row.requested_support:g}%');values.append(row.median/1000)
    bars(d,values,labels,100,170,900,320,'Median fit + rule generation time (seconds)',rotate=25)
    note(d,'Both mine unbounded lengths, then report rules of at most three items. Local timings are implementation/hardware dependent.');save(d,figures/'11_rule_runtime.svg')
    if (models/'association_validation_grid.csv').exists():
        grid=pd.read_csv(models/'association_validation_grid.csv');chosen=json.loads((models/'selected_rule_config.json').read_text())
        top=grid.head(6).iloc[::-1];labels=[f"support={row.min_support:g}, length<={int(row.max_len)}, confidence>={row.min_confidence:g}" for row in top.itertuples()]
        labels.insert(0,'Train popularity baseline');values=[100*chosen['baseline_popularity']['hit_rate_at_5']]+(top['hit_rate_at_5']*100).tolist()
        d=figure('Validation masked-basket completion at K=5','One hidden product per eligible invoice; includes hidden products unseen in train.')
        bars(d,values,labels,390,110,620,390,'Validation HitRate@5 (%)',horizontal=True)
        note(d,'Validation is used to choose parameters; these are selection results, not unbiased final-test estimates.');save(d,figures/'12_validation_rule_selection.svg')
    if (models/'segment_vs_global_validation.csv').exists():
        comparison=pd.read_csv(models/'segment_vs_global_validation.csv')
        d=figure('Do segment-specific rules improve basket completion?','Same 2,274 validation baskets from customers with a frozen train profile; same popularity fallback.')
        bars(d,(comparison['hit_rate_at_5']*100).tolist(),['Popularity','Global rules, identified cohort','Segment-specific rules'],130,150,830,340,'Validation HitRate@5 (%)')
        note(d,'Validation comparison only. Segment rules are not assumed to outperform global rules.');save(d,figures/'13_segment_rule_comparison.svg')
    paired_path=ROOT/'results/experiments/paired_subset_rules/benchmark.csv'
    if paired_path.exists():
        paired=pd.read_csv(paired_path).groupby(['algorithm','requested_support'])['fit_and_rule_generation_ms'].agg(['median','min','max']).reset_index()
        paired.to_csv(tables/'paired_subset_runtime_summary.csv',index=False)
        d=figure('Matched 500-invoice runtime comparison','Fixed seed-42 subset of train. Both algorithms return the same nontrivial rules and counts.')
        labels=[f'{row.algorithm}, support={100*row.requested_support:g}%' for row in paired.itertuples()]
        bars(d,(paired['median']/1000).tolist(),labels,100,170,900,320,'Median fit + rule generation (seconds)',rotate=25)
        note(d,'Three repetitions with alternating algorithm order. Local timings are not universal algorithm speed guarantees.');save(d,figures/'15_paired_subset_runtime.svg')
    print(json.dumps({'svg_figures':len(list(figures.glob('*.svg'))),'source_tables':len(list(tables.glob('*'))),'top_10pct_customer_purchase_share':top_share},indent=2))

if __name__=='__main__':main()
