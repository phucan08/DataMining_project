"""Freeze selected artifacts, score final test once, or verify saved results."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.final_evaluation import bootstrap_hit_rates,digest,score_cases,summarize,verify_records
from src.model_metrics import decode_rules,evaluate_rule_stability,masked_cases,popularity,rule_index

TABLES=ROOT/'results/tables/final_test'
LOCK=ROOT/'results/models/final_evaluation_lock.json'
RECEIPT=TABLES/'evaluation_receipt.json'


def source_paths():
    fixed=['configs/cleaning_policy.json','configs/experiment_protocol.json',
           'configs/final_evaluation_protocol.json','data/processed/prepared_manifest.json',
           'data/raw/Online Retail.xlsx','src/model_metrics.py','src/final_evaluation.py',
           'scripts/evaluate_final_test.py','results/tables/models/selected_rule_config.json',
           'results/tables/models/selected_global_rules.csv','results/tables/models/global_identified_rules.csv',
           'results/tables/models/Segment_1_rules.csv','results/tables/models/Segment_2_rules.csv',
           'results/tables/models/cluster_assignments_train.csv','results/models/selected_kmeans_metadata.json',
           'results/models/selected_weka_kmeans.model']
    prepared=json.loads((ROOT/'data/processed/prepared_manifest.json').read_text())
    fixed += ['data/processed/'+row['name'] for row in prepared['files']]
    return sorted(set(fixed))


def freeze():
    if LOCK.exists():
        lock=json.loads(LOCK.read_text())
        verify_records(ROOT,lock['files'])
        return lock
    if RECEIPT.exists():
        raise RuntimeError('A result exists without its original freeze lock.')
    prepared=json.loads((ROOT/'data/processed/prepared_manifest.json').read_text())
    assert digest(ROOT/'data/raw/Online Retail.xlsx')==prepared['raw_sha256']
    for row in prepared['files']:
        assert digest(ROOT/'data/processed'/row['name'])==row['sha256']
    trained=json.loads((ROOT/'results/experiments/experiment_manifest.json').read_text())
    verify_records(ROOT,trained['files'])
    lock={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
          'purpose':'final_test_evaluation_of_train_only_frozen_models_without_refitting',
          'files':[{'path':name,'sha256':digest(ROOT/name)} for name in source_paths()]}
    with LOCK.open('x',encoding='utf-8') as stream:json.dump(lock,stream,indent=2)
    return lock


def load_rules(name,transactions):
    frame=pd.read_csv(ROOT/'results/tables/models'/f'{name}_rules.csv',
                      dtype={'antecedent':'string','consequent':'string'})
    return decode_rules(frame,transactions)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-only',action='store_true')
    args=parser.parse_args()
    freeze()
    if args.freeze_only:
        print(json.dumps({'frozen':True,'lock':str(LOCK.relative_to(ROOT))}));return
    if RECEIPT.exists():
        receipt=json.loads(RECEIPT.read_text())
        assert digest(LOCK)==receipt['freeze_lock_sha256']
        verify_records(ROOT,receipt['files'])
        print(json.dumps({'action':'verified_saved_results_without_rescoring','summary':receipt['summary']}));return
    marker=TABLES/'evaluation_started.json'
    if marker.exists():
        raise RuntimeError('A prior scoring attempt started without a complete receipt; inspect its outputs before any further scoring.')
    protocol=json.loads((ROOT/'configs/final_evaluation_protocol.json').read_text())
    k=protocol['recommendation_k']; seed=protocol['mask_seed']
    baskets=pd.read_csv(ROOT/'data/processed/baskets.csv',dtype={'InvoiceNo':'string','CustomerID':'string'})
    items=pd.read_csv(ROOT/'data/processed/basket_items.csv.gz',dtype={'InvoiceNo':'string','StockCode':'string'})
    grouped=items.groupby('InvoiceNo')['StockCode'].agg(set).to_dict()
    assignments=pd.read_csv(ROOT/'results/tables/models/cluster_assignments_train.csv',dtype={'CustomerID':'string'})
    customer_segment=assignments.set_index('CustomerID')['Segment'].to_dict()
    baskets['Segment']=baskets['CustomerID'].map(customer_segment)
    train=baskets.loc[baskets['Split'].eq('train')].sort_values('InvoiceNo')
    test=baskets.loc[baskets['Split'].eq('test')].sort_values('InvoiceNo').copy()
    test['CustomerGroup']=np.where(test['Segment'].notna(),'train_profile_customers',
                                  np.where(test['CustomerID'].notna(),'new_identified_customers','missing_customer_id'))
    assert test['InvoiceTimestamp'].ge('2011-10-01').all() and test['InvoiceTimestamp'].lt('2011-12-10').all()
    metadata={row.InvoiceNo:('' if pd.isna(row.CustomerID) else str(row.CustomerID),
                            '' if pd.isna(row.Segment) else str(row.Segment)) for row in test.itertuples()}
    all_train=[grouped[i] for i in train['InvoiceNo']]
    known_train=train.loc[train['Segment'].notna()]
    known_transactions=[grouped[i] for i in known_train['InvoiceNo']]
    rules_all=load_rules('selected_global',all_train)
    rules_known=load_rules('global_identified',known_transactions)
    segment_rules={name:load_rules(name,[grouped[i] for i in known_train.loc[known_train['Segment'].eq(name),'InvoiceNo']])
                   for name in sorted(assignments['Segment'].unique())}
    indexes={'global_rules':rule_index(rules_all),'global_identified_rules':rule_index(rules_known),
             'segment_rules':{name:rule_index(rules) for name,rules in segment_rules.items()},'popularity':{}}
    all_pop=popularity(all_train);known_pop=popularity(known_transactions)
    cases=masked_cases(test['InvoiceNo'],[grouped[i] for i in test['InvoiceNo']],seed)
    known_ids=set(test.loc[test['Segment'].notna(),'InvoiceNo'])
    known_cases=[case for case in cases if case[0] in known_ids]
    TABLES.mkdir(parents=True,exist_ok=True)
    with marker.open('x',encoding='utf-8') as stream:
        json.dump({'started_at_utc':datetime.now(timezone.utc).isoformat(),'freeze_lock_sha256':digest(LOCK)},stream)
    frames=[]
    for name in ['popularity','global_rules']:
        frames.append(score_cases(cases,metadata,indexes[name],all_pop,name,'all_baskets',k,all_pop))
    for name in ['popularity','global_identified_rules','segment_rules']:
        frames.append(score_cases(known_cases,metadata,indexes[name],known_pop,name,'train_profile_customers',k,all_pop))
    predictions=pd.concat(frames,ignore_index=True)
    customer_groups=test.set_index('InvoiceNo')['CustomerGroup'].to_dict()
    predictions['CustomerGroup']=predictions['InvoiceNo'].map(customer_groups)
    summaries=[]
    for (cohort,method),frame in predictions.groupby(['cohort','method']):
        summaries.append({'cohort':cohort,'method':method,**summarize(frame,k)})
    for group,rows in predictions.loc[predictions['cohort'].eq('all_baskets')].groupby('CustomerGroup'):
        for method,frame in rows.groupby('method'):
            summaries.append({'cohort':'all_model/'+group,'method':method,**summarize(frame,k)})
    for segment,rows in predictions.loc[predictions['cohort'].eq('train_profile_customers')].groupby('Segment'):
        for method,frame in rows.groupby('method'):
            summaries.append({'cohort':'segment/'+segment,'method':method,**summarize(frame,k)})
    metrics=pd.DataFrame(summaries)
    uncertainty=protocol['uncertainty'];intervals=[];contrasts=[]
    for cohort,names,left,right in [('all_baskets',['popularity','global_rules'],'global_rules','popularity'),
                                  ('train_profile_customers',['popularity','global_identified_rules','segment_rules'],'segment_rules','global_identified_rules')]:
        names,samples=bootstrap_hit_rates(predictions.loc[predictions['cohort'].eq(cohort)],names,
                                         uncertainty['replicates'],uncertainty['seed'])
        points=metrics.loc[metrics['cohort'].eq(cohort)].set_index('method')
        for i,name in enumerate(names):
            lo,hi=np.quantile(samples[:,i],[.025,.975])
            intervals.append({'cohort':cohort,'method':name,'estimate':points.loc[name,'hit_rate_at_5'],
                              'ci95_lower':lo,'ci95_upper':hi,'replicates':uncertainty['replicates']})
        delta=samples[:,names.index(left)]-samples[:,names.index(right)]
        lo,hi=np.quantile(delta,[.025,.975])
        contrasts.append({'cohort':cohort,'contrast':left+' minus '+right,
                          'estimate_difference':points.loc[left,'hit_rate_at_5']-points.loc[right,'hit_rate_at_5'],
                          'ci95_lower':lo,'ci95_upper':hi})
    TABLES.mkdir(parents=True,exist_ok=True)
    predictions.to_csv(TABLES/'case_predictions.csv.gz',index=False,compression='gzip')
    metrics.to_csv(TABLES/'completion_metrics.csv',index=False)
    pd.DataFrame(intervals).to_csv(TABLES/'bootstrap_intervals.csv',index=False)
    pd.DataFrame(contrasts).to_csv(TABLES/'paired_bootstrap_contrasts.csv',index=False)
    cohort=[]
    for name,subset in [('all_baskets',test),*list(test.groupby('CustomerGroup'))]:
        ids=set(subset['InvoiceNo']);eligible=[case for case in cases if case[0] in ids]
        cohort.append({'cohort':name,'total_baskets':len(subset),'eligible_baskets':len(eligible),
                       'single_item_baskets':int(subset['UniqueProducts'].lt(2).sum()),
                       'identified_customers':subset['CustomerID'].nunique(),
                       'targets_unseen_in_train':sum(target not in all_pop for _,_,target in eligible)})
    pd.DataFrame(cohort).to_csv(TABLES/'cohort_audit.csv',index=False)
    stability=[]
    for name,rules,subset in [('selected_global',rules_all,test),('global_identified',rules_known,test.loc[test['Segment'].notna()]),
                             *[(name,rules,test.loc[test['Segment'].eq(name)]) for name,rules in segment_rules.items()]]:
        stable=evaluate_rule_stability(rules,[grouped[i] for i in subset['InvoiceNo']],prefix='test')
        stable.drop(columns=['A','B']).to_csv(TABLES/f'{name}_rule_stability.csv',index=False)
        stability.append({'group':name,'fixed_rules':len(stable),'test_baskets':len(subset),
                          'test_antecedent_absent':int(stable['test_count_a'].eq(0).sum()),
                          'test_joint_count_below_20':int(stable['test_count_ab'].lt(20).sum()),
                          'test_joint_count_at_least_20':int(stable['test_count_ab'].ge(20).sum()),
                          'test_lift_above_1':int(stable['test_lift'].gt(1).sum())})
    pd.DataFrame(stability).to_csv(TABLES/'rule_stability_summary.csv',index=False)
    # Store examples by deterministic invoice ordering, not by favorable outcomes.
    examples=predictions.loc[predictions['cohort'].eq('all_baskets')&predictions['method'].eq('global_rules')&predictions['hit'].eq(0)].copy()
    examples.head(10).to_csv(TABLES/'error_examples.csv',index=False)
    summary={'test_scored':True,'models_refitted':False,'test_baskets':len(test),
             'eligible_all_baskets':len(cases),'eligible_train_profile_baskets':len(known_cases),
             'mask_seed':seed,'recommendation_k':k,'bootstrap_replicates':uncertainty['replicates'],
             'metrics':metrics.loc[metrics['cohort'].isin(['all_baskets','train_profile_customers'])].to_dict('records'),
             'contrasts':contrasts}
    (TABLES/'evaluation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    verify_records(ROOT,json.loads(LOCK.read_text())['files'])
    receipt={'evaluated_at_utc':datetime.now(timezone.utc).isoformat(),'freeze_lock_sha256':digest(LOCK),
             'summary':summary,'files':[{'path':str(path.relative_to(ROOT)),'sha256':digest(path)}
                                      for path in sorted(TABLES.iterdir()) if path.is_file() and path!=RECEIPT]}
    with RECEIPT.open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
