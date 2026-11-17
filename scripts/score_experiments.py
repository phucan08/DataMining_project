"""Verify Weka outputs, select on validation/train criteria and freeze models."""
from __future__ import annotations
import itertools,json,math,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.model_metrics import (adjusted_rand,bitsets,item_count,completion_metrics,decode_rules,evaluate_rule_stability,masked_cases,pairwise_distances,popularity,silhouette)


def load_inputs():
    baskets=pd.read_csv(ROOT/'data/processed/baskets.csv',dtype={'InvoiceNo':'string','CustomerID':'string'})
    items=pd.read_csv(ROOT/'data/processed/basket_items.csv.gz',dtype={'InvoiceNo':'string','StockCode':'string'})
    grouped=items.groupby('InvoiceNo')['StockCode'].agg(set).to_dict()
    return baskets,grouped

def select_rules(frame,support,max_len,confidence,protocol):
    rule=protocol['rules']
    return frame.loc[(frame['max_len']<=max_len)&frame['B'].map(len).eq(1)&(frame['confidence']>=confidence-1e-12)&(frame['lift']>=rule['minimum_lift'])&(frame['count_ab']>=rule['minimum_absolute_count'])].copy()

def export_rules(frame,path,catalog=None):
    result=frame.drop(columns=['A','B'],errors='ignore').copy()
    if catalog is not None:
        result['antecedent_names']=result['antecedent'].map(lambda text:' + '.join(catalog.get(code,code) for code in text.split('|')))
        result['consequent_names']=result['consequent'].map(lambda text:' + '.join(catalog.get(code,code) for code in text.split('|')))
    result.to_csv(path,index=False)

def score_rules(baskets,grouped,protocol,output):
    work=ROOT/'results/experiments/global_rules'
    ids={split:baskets.loc[baskets['Split'].eq(split)].sort_values('InvoiceNo')['InvoiceNo'].tolist() for split in ['train','validation']}
    transactions={split:[grouped[invoice] for invoice in values] for split,values in ids.items()}
    cases=masked_cases(ids['validation'],transactions['validation'],protocol['rules']['completion_seed'])
    popular=popularity(transactions['train'])
    pools={};comparisons=[];candidates=[]
    for s,support in enumerate(protocol['rules']['requested_min_support_grid']):
        fp=decode_rules(pd.read_csv(work/f'fpgrowth_s{s}_rules.csv'),transactions['train'])
        required=math.ceil(support*len(transactions['train'])-1e-10)
        assert fp['count_ab'].ge(required).all()
        pools[support]=fp
        apriori=work/f'apriori_s{s}_rules.csv'
        match=None
        if apriori.exists():
            ap=decode_rules(pd.read_csv(apriori),transactions['train'])
            columns=['antecedent','consequent','count_a','count_b','count_ab','n_transactions']
            pd.testing.assert_frame_equal(ap[columns].sort_values(columns[:2]).reset_index(drop=True),fp[columns].sort_values(columns[:2]).reset_index(drop=True),check_dtype=False)
            match=True
        comparisons.append({'requested_support':support,'minimum_count':required,'fp_reported_max3_rules':len(fp),'apriori_completed':apriori.exists(),'same_rules_and_counts':match,'all_fp_counts_verified_independently':True})
        for length,confidence in itertools.product(protocol['rules']['reported_max_itemset_length_grid'],protocol['rules']['confidence_grid']):
            rules=select_rules(fp,support,length,confidence,protocol)
            metrics=completion_metrics(cases,rules,popular,protocol['rules']['recommendation_k'])
            candidates.append({'min_support':support,'max_len':length,'min_confidence':confidence,'rule_count':len(rules),**metrics})
    pd.DataFrame(comparisons).to_csv(output/'association_algorithm_checks.csv',index=False)
    scores=pd.DataFrame(candidates).sort_values(['hit_rate_at_5','rule_count','max_len','min_support','min_confidence'],ascending=[False,True,True,False,False]).reset_index(drop=True)
    scores.to_csv(output/'association_validation_grid.csv',index=False)
    chosen=scores.iloc[0].to_dict()
    selected=select_rules(pools[chosen['min_support']],chosen['min_support'],int(chosen['max_len']),chosen['min_confidence'],protocol)
    selected=evaluate_rule_stability(selected,transactions['validation'])
    catalog=pd.read_csv(ROOT/'data/processed/product_catalog_train.csv',dtype={'StockCode':'string'}).set_index('StockCode')['DisplayName'].to_dict()
    export_rules(selected.sort_values(['count_ab','confidence','lift'],ascending=False),output/'selected_global_rules.csv',catalog)
    baseline=completion_metrics(cases,selected.iloc[:0],popular,protocol['rules']['recommendation_k'])
    chosen.update({'baseline_popularity':baseline,'selection_split':'validation','validation_used_for_selection_not_unbiased_final_test':True,'eligible_validation_baskets':len(cases),'hidden_targets_outside_train_vocabulary':sum(target not in popular for _,_,target in cases),'rule_counts_independently_verified':True,'final_test_scored':False})
    (output/'selected_rule_config.json').write_text(json.dumps(chosen,indent=2)+'\n',encoding='utf-8')
    return chosen

def score_clusters(baskets,protocol,output):
    work=ROOT/'results/experiments/kmeans'
    fits=pd.read_csv(work/'weka_kmeans_fits.csv');centers=pd.read_csv(work/'weka_kmeans_centers.csv')
    features=pd.read_csv(ROOT/'data/processed/rfm_train_features.csv',dtype={'CustomerID':'string'})
    rfm=pd.read_csv(ROOT/'data/processed/rfm_train.csv',dtype={'CustomerID':'string'})
    assert features['CustomerID'].tolist()==rfm['CustomerID'].tolist()
    values=features.iloc[:,1:].to_numpy();distances=pairwise_distances(values)
    summaries=[];all_scores=[]
    for k in protocol['clustering']['k_grid']:
        labels_by_seed={}
        for seed in protocol['clustering']['base_seeds']:
            labels=pd.read_csv(work/f'k{k}_seed{seed}_labels.csv')['raw_cluster'].to_numpy(dtype=int)
            centroid=centers.loc[centers['k'].eq(k)&centers['base_seed'].eq(seed)].sort_values('raw_cluster').iloc[:,3:].to_numpy()
            sse=float(np.sum((values-centroid[labels])**2))
            fit=fits.loc[fits['k'].eq(k)&fits['base_seed'].eq(seed)].iloc[0]
            assert np.isclose(sse,fit['sse'],rtol=1e-8,atol=1e-7)
            score=silhouette(distances,labels);sizes=np.bincount(labels,minlength=k)
            labels_by_seed[seed]=labels
            all_scores.append({'k':k,'seed':seed,'silhouette':score,'sse':sse,'smallest_cluster_fraction':float(sizes.min()/len(labels))})
        pair_ari=[adjusted_rand(labels_by_seed[a],labels_by_seed[b]) for a,b in itertools.combinations(labels_by_seed,2)]
        subset=pd.DataFrame([row for row in all_scores if row['k']==k])
        summaries.append({'k':k,'mean_silhouette':float(subset['silhouette'].mean()),'sd_silhouette':float(subset['silhouette'].std(ddof=0)),'mean_sse':float(subset['sse'].mean()),'mean_pairwise_ARI':float(np.mean(pair_ari)),'minimum_cluster_fraction_across_seeds':float(subset['smallest_cluster_fraction'].min())})
    scores=pd.DataFrame(summaries)
    cp=protocol['clustering']
    scores['eligible']=scores['mean_pairwise_ARI'].ge(cp['minimum_mean_pairwise_ARI'])&scores['minimum_cluster_fraction_across_seeds'].ge(cp['minimum_cluster_fraction'])
    scores.to_csv(output/'clustering_k_comparison.csv',index=False)
    pd.DataFrame(all_scores).to_csv(output/'clustering_seed_scores.csv',index=False)
    eligible=scores.loc[scores['eligible']]
    if eligible.empty:raise RuntimeError('No k meets predeclared stability/size criteria; inspect before proceeding.')
    best=eligible['mean_silhouette'].max();chosen_k=int(eligible.loc[eligible['mean_silhouette']>=best-0.005,'k'].min())
    raw_labels=pd.read_csv(work/f'k{chosen_k}_seed42_labels.csv')['raw_cluster'].to_numpy(dtype=int)
    assignments=rfm.copy();assignments['WekaCluster']=raw_labels
    order=assignments.groupby('WekaCluster')['Monetary'].median().sort_values(ascending=False).index
    mapping={int(raw):f'Segment_{i+1}' for i,raw in enumerate(order)}
    assignments['Segment']=assignments['WekaCluster'].map(mapping)
    profiles=assignments.groupby('Segment').agg(customers=('CustomerID','size'),median_recency=('Recency','median'),median_frequency=('Frequency','median'),median_monetary=('Monetary','median'),total_monetary=('Monetary','sum')).reset_index()
    profiles['customer_fraction']=profiles['customers']/len(assignments)
    profiles['gross_purchase_value_fraction']=profiles['total_monetary']/assignments['Monetary'].sum()
    medians=rfm[['Recency','Frequency','Monetary']].median()
    profiles['description']=profiles.apply(lambda row:('more recent' if row['median_recency']<=medians['Recency'] else 'less recent')+', '+('more frequent' if row['median_frequency']>=medians['Frequency'] else 'less frequent')+', '+('higher gross spend' if row['median_monetary']>=medians['Monetary'] else 'lower gross spend'),axis=1)
    names=profiles.set_index('Segment')['description'].to_dict();assignments['SegmentDescription']=assignments['Segment'].map(names)
    assignments.to_csv(output/'cluster_assignments_train.csv',index=False);profiles.to_csv(output/'cluster_profiles.csv',index=False)
    models=ROOT/'results/models';models.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(work/f'k{chosen_k}_seed42.model',models/'selected_weka_kmeans.model')
    center=centers.loc[centers['k'].eq(chosen_k)&centers['base_seed'].eq(42)]
    model={'k':chosen_k,'base_seed':42,'best_actual_initialization_seed':int(fits.loc[fits['k'].eq(chosen_k)&fits['base_seed'].eq(42),'best_actual_seed'].iloc[0]),'raw_cluster_to_segment':mapping,'centers_standardized':center.sort_values('raw_cluster').iloc[:,3:].to_numpy().tolist(),'feature_names':list(features.columns[1:]),'distance':'euclidean_without_additional_normalization','selection_uses_train_internal_metrics_only':True,'full_silhouette_customers':len(rfm),'selected_k_metrics':scores.loc[scores['k'].eq(chosen_k)].iloc[0].to_dict(),'final_test_scored':False}
    (models/'selected_kmeans_metadata.json').write_text(json.dumps(model,indent=2)+'\n',encoding='utf-8')
    return model

def main():
    protocol=json.loads((ROOT/'configs/experiment_protocol.json').read_text())
    output=ROOT/'results/tables/models';output.mkdir(parents=True,exist_ok=True)
    baskets,grouped=load_inputs()
    rules=score_rules(baskets,grouped,protocol,output)
    clusters=score_clusters(baskets,protocol,output)
    summary={'global_rules':rules,'clustering':clusters,'final_test_scored':False}
    (output/'experiment_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'selected_rule_parameters':{key:rules[key] for key in ['min_support','max_len','min_confidence','rule_count','hit_rate_at_5']},'popularity_validation_hit_rate':rules['baseline_popularity']['hit_rate_at_5'],'selected_k':clusters['k'],'final_test_scored':False},indent=2))

if __name__=='__main__':main()
