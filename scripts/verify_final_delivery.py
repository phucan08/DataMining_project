"""Check final tables, frozen provenance, rendered figures and report links."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.final_evaluation import digest,verify_records


def main():
    base=ROOT/'results/tables/final_test'
    receipt=json.loads((base/'evaluation_receipt.json').read_text())
    lock=ROOT/'results/models/final_evaluation_lock.json'
    assert digest(lock)==receipt['freeze_lock_sha256']
    verify_records(ROOT,json.loads(lock.read_text())['files']);verify_records(ROOT,receipt['files'])
    predictions=pd.read_csv(base/'case_predictions.csv.gz',dtype={'InvoiceNo':'string','CustomerID':'string'})
    metrics=pd.read_csv(base/'completion_metrics.csv')
    for cohort in ['all_baskets','train_profile_customers']:
        subset=predictions.loc[predictions['cohort'].eq(cohort)]
        targets=subset.pivot(index='InvoiceNo',columns='method',values='target')
        assert targets.notna().all().all()
        assert targets.nunique(axis=1).eq(1).all()
        for method,frame in subset.groupby('method'):
            row=metrics.loc[metrics['cohort'].eq(cohort)&metrics['method'].eq(method)].iloc[0]
            assert len(frame)==row['eligible_baskets']
            assert frame['hit'].sum()==row['hits']
            assert np.isclose(frame['hit'].mean(),row['hit_rate_at_5'])
            assert np.isclose(row['recall_at_5'],row['hit_rate_at_5'])
            assert np.isclose(row['precision_at_5_fixed_denominator'],row['hit_rate_at_5']/5)
            assert np.isclose(frame['used_rule'].mean(),row['rule_coverage'])
    audit=pd.read_csv(base/'cohort_audit.csv').set_index('cohort')
    all_row=audit.loc['all_baskets'];other=audit.drop(index='all_baskets')
    for column in ['total_baskets','eligible_baskets','single_item_baskets','targets_unseen_in_train']:
        assert all_row[column]==other[column].sum()
    png={p.stem for p in (ROOT/'results/figures').glob('*.png')}
    svg={p.stem for p in (ROOT/'results/figures').glob('*.svg')}
    assert png==svg and '16_final_test_comparison' in png
    documents=['README.md','TODO.md','docs/progress.md','docs/eda_report.md',
               'docs/experiment_report.md','docs/final_evaluation_report.md','report/project_report.md']
    checked_links=0
    for name in documents:
        path=ROOT/name;content=path.read_text(encoding='utf-8')
        assert '\ufffd' not in content,name
        for target in re.findall(r'\]\(([^)]+)\)',content):
            target=target.strip('<>')
            if target.startswith(('http:','https:','mailto:','#')):continue
            assert (path.parent/target.split('#')[0]).exists(),(name,target)
            checked_links+=1
    project=json.loads((ROOT/'configs/project.json').read_text())
    assert project['evaluation']['final_test_scored'] is True
    artifacts=documents+['configs/project.json','configs/final_evaluation_protocol.json',
                         'results/models/final_evaluation_lock.json',
                         'results/tables/final_test/evaluation_receipt.json',
                         'results/figures/16_final_test_comparison.svg',
                         'results/figures/16_final_test_comparison.png',
                         'scripts/report_final_evaluation.py','scripts/run_final_evaluation.ps1',
                         'scripts/verify_final_delivery.py']
    manifest={'final_test_receipt_sha256':digest(base/'evaluation_receipt.json'),
              'test_scored':True,'frozen_models_and_data_verified':True,
              'files':[{'path':name,'sha256':digest(ROOT/name)} for name in artifacts]}
    (ROOT/'results/final_delivery_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'frozen_sources_and_saved_test_outputs_verified':True,'same_targets_across_methods':True,
                      'metric_arithmetic_verified':True,'figures_png_svg':len(png),'document_links_checked':checked_links,
                      'delivery_manifest':'results/final_delivery_manifest.json'}))


if __name__=='__main__':main()
