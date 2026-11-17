"""Compare global and segment rules on the same known-customer cohort."""
from __future__ import annotations
import json,math,subprocess,sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.model_metrics import completion_metrics,decode_rules,evaluate_rule_stability,masked_cases,popularity,recommend,rule_index
from run_weka_fits import command
from score_experiments import export_rules,load_inputs,select_rules


def main():
    protocol=json.loads((ROOT/'configs/experiment_protocol.json').read_text())
    chosen=json.loads((ROOT/'results/tables/models/selected_rule_config.json').read_text())
    assignments=pd.read_csv(ROOT/'results/tables/models/cluster_assignments_train.csv',dtype={'CustomerID':'string'})
    customer_segment=assignments.set_index('CustomerID')['Segment'].to_dict()
    baskets,grouped=load_inputs()
    baskets['Segment']=baskets['CustomerID'].map(customer_segment)
    train=baskets.loc[baskets['Split'].eq('train')&baskets['Segment'].notna()].sort_values('InvoiceNo')
    validation=baskets.loc[baskets['Split'].eq('validation')&baskets['Segment'].notna()].sort_values('InvoiceNo')
    validation_segment=validation.set_index('InvoiceNo')['Segment'].to_dict()
    codes=pd.read_csv(ROOT/'data/processed/product_catalog_train.csv',dtype={'StockCode':'string'})
    code_index=dict(zip(codes['StockCode'],codes['ColumnIndex']))
    catalog=codes.set_index('StockCode')['DisplayName'].to_dict()
    base=ROOT/'results/experiments/segment_rules';base.mkdir(parents=True,exist_ok=True)
    tables=ROOT/'results/tables/models'
    rules_by_group={};summaries=[]
    for name in ['global_identified',*sorted(train['Segment'].unique())]:
        subset=train if name=='global_identified' else train.loc[train['Segment'].eq(name)]
        ids=subset['InvoiceNo'].tolist();transactions=[grouped[invoice] for invoice in ids]
        directory=base/name;directory.mkdir(parents=True,exist_ok=True)
        path=directory/'transactions.txt'
        path.write_text('\n'.join(' '.join(str(code_index[item]) for item in sorted(items)) for items in transactions)+'\n')
        support=max(float(chosen['min_support']),protocol['segment_rules']['minimum_absolute_count']/len(ids))
        with (directory/'console.log').open('w',encoding='utf-8') as stream:
            subprocess.run(command('rules',ROOT/'results/experiments/inputs/product_codes.txt',path,directory,support,1,'fpgrowth_bounded_only'),stdout=stream,stderr=subprocess.STDOUT,cwd=ROOT,check=True,timeout=60)
        all_rules=decode_rules(pd.read_csv(directory/'fpgrowth_s0_rules.csv'),transactions)
        selected=select_rules(all_rules,support,int(chosen['max_len']),float(chosen['min_confidence']),protocol)
        valid=validation if name=='global_identified' else validation.loc[validation['Segment'].eq(name)]
        selected=evaluate_rule_stability(selected,[grouped[invoice] for invoice in valid['InvoiceNo']])
        rules_by_group[name]=selected
        export_rules(selected.sort_values(['count_ab','confidence'],ascending=False),tables/f'{name}_rules.csv',catalog)
        summaries.append({'group':name,'train_baskets':len(ids),'validation_baskets':len(valid),'selected_rules':len(selected),'minimum_count':math.ceil(support*len(ids)-1e-10),'relative_support':support})
    cases=masked_cases(validation['InvoiceNo'],[grouped[invoice] for invoice in validation['InvoiceNo']],protocol['rules']['completion_seed'])
    popular=popularity([grouped[invoice] for invoice in train['InvoiceNo']])
    k=protocol['rules']['recommendation_k']
    output=[]
    for name,rules in [('popularity',rules_by_group['global_identified'].iloc[:0]),('global_rules_identified',rules_by_group['global_identified'])]:
        output.append({'method':name,**completion_metrics(cases,rules,popular,k)})
    indexes={name:rule_index(rules) for name,rules in rules_by_group.items() if name!='global_identified'}
    hits=covered=recommendations=0
    for invoice,observed,target in cases:
        ranked,used=recommend(observed,indexes[validation_segment[invoice]],popular,k)
        hits+=target in ranked;covered+=used;recommendations+=len(ranked)
    output.append({'method':'segment_rules','eligible_baskets':len(cases),'hits':hits,'hit_rate_at_5':hits/len(cases),'rule_coverage':covered/len(cases),'baskets_with_rule_recommendation':covered,'returned_recommendations':recommendations})
    pd.DataFrame(output).to_csv(tables/'segment_vs_global_validation.csv',index=False)
    pd.DataFrame(summaries).to_csv(tables/'segment_rule_summary.csv',index=False)
    metadata={'comparison':'same_train_profile_customer_cohort; same_masked_baskets; same_candidate_vocabulary_and_popularity_fallback','train_baskets':len(train),'validation_baskets_in_cohort':len(validation),'eligible_masked_validation_baskets':len(cases),'validation_baskets_outside_cohort':int(baskets['Split'].eq('validation').sum()-len(validation)),'customer_segments_frozen_at':'2011-08-01','hyperparameters_reused_from_global_selection':True,'final_test_scored':False}
    (tables/'segment_comparison_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({'validation_results':output,'cohort':metadata},indent=2))

if __name__=='__main__':main()
