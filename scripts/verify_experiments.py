"""Verify trained outputs, paired Weka results and frozen-data integrity."""
from __future__ import annotations
import hashlib,importlib.metadata,json,os,subprocess,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.model_metrics import decode_rules
from run_weka_fits import JAVA,JAR

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    lock_path=ROOT/'results/models/final_evaluation_lock.json'
    if lock_path.exists():
        from src.final_evaluation import verify_records
        lock=json.loads(lock_path.read_text())
        verify_records(ROOT,lock['files'])
        receipt=json.loads((ROOT/'results/tables/final_test/evaluation_receipt.json').read_text())
        assert digest(lock_path)==receipt['freeze_lock_sha256']
        verify_records(ROOT,receipt['files'])
        print(json.dumps({'frozen_train_and_final_test_artifacts_verified':True,'raw_and_prepared_data_unchanged':True,'final_test_scored':True,'no_artifacts_overwritten':True}))
        return
    prepared=json.loads((ROOT/'data/processed/prepared_manifest.json').read_text())
    assert digest(ROOT/'data/raw/Online Retail.xlsx')==prepared['raw_sha256']
    for record in prepared['files']:
        assert digest(ROOT/'data/processed'/record['name'])==record['sha256'],record['name']
    codes=(ROOT/'results/experiments/inputs/product_codes.txt').read_text().splitlines()
    transactions=[{codes[int(item)] for item in row.split()} for row in (ROOT/'results/experiments/inputs/paired_subset_transactions.txt').read_text().splitlines()]
    paired=[]
    for i,support in enumerate([.02,.05]):
        directory=ROOT/'results/experiments/paired_subset_rules'
        a=decode_rules(pd.read_csv(directory/f'apriori_s{i}_rules.csv'),transactions)
        b=decode_rules(pd.read_csv(directory/f'fpgrowth_s{i}_rules.csv'),transactions)
        cols=['antecedent','consequent','count_a','count_b','count_ab','n_transactions']
        pd.testing.assert_frame_equal(a[cols].sort_values(cols[:2]).reset_index(drop=True),b[cols].sort_values(cols[:2]).reset_index(drop=True),check_dtype=False)
        paired.append({'support':support,'baskets':len(transactions),'rules_max3':len(a),'identical_rules_and_counts':True,'all_counts_independently_verified':True})
    output=ROOT/'results/tables/models'
    pd.DataFrame(paired).to_csv(output/'paired_algorithm_checks.csv',index=False)
    selected=json.loads((output/'selected_rule_config.json').read_text())
    assert selected['final_test_scored'] is False
    comparison=pd.read_csv(output/'segment_vs_global_validation.csv')
    assert comparison['eligible_baskets'].nunique()==1
    assignments=pd.read_csv(output/'cluster_assignments_train.csv',dtype={'CustomerID':'string'})
    features=pd.read_csv(ROOT/'data/processed/rfm_train_features.csv',dtype={'CustomerID':'string'})
    assert assignments['CustomerID'].tolist()==features['CustomerID'].tolist()
    assert assignments['CustomerID'].is_unique
    profiles=pd.read_csv(output/'cluster_profiles.csv')
    assert profiles['customers'].sum()==len(features)
    assert np.isclose(profiles['gross_purchase_value_fraction'].sum(),1)
    figures=list((ROOT/'results/figures').glob('*.png'))
    png_stems={path.stem for path in figures}
    svg_stems={path.stem for path in (ROOT/'results/figures').glob('*.svg')}
    assert svg_stems==png_stems
    assert {'01_monthly_purchases','08_k_selection','13_segment_rule_comparison','15_paired_subset_runtime'}.issubset(png_stems)
    packages={name:importlib.metadata.version(name) for name in ['pandas','numpy','reportlab','Pillow']}
    version=subprocess.run([str(JAVA),'-version'],capture_output=True,text=True,check=True).stderr.splitlines()[0]
    environment={'python':sys.version.split()[0],'packages':packages,'java':version,'java_executable':str(JAVA),'weka_jar':str(JAR),'weka_version':'3.8.7','weka_jar_sha256':digest(JAR),'graphics':'ReportLab SVG charts rendered to PNG with Sharp','sklearn_mlxtend_required_for_this_workflow':False}
    (ROOT/'results/tables/model_environment.json').write_text(json.dumps(environment,indent=2)+'\n')
    manifest={'raw_sha256':prepared['raw_sha256'],'prepared_manifest_sha256':digest(ROOT/'data/processed/prepared_manifest.json'),'protocol_sha256':digest(ROOT/'configs/experiment_protocol.json'),'weka_jar_sha256':digest(JAR),'final_test_scored':False,'files':[]}
    for directory in [ROOT/'results/tables/models',ROOT/'results/models',ROOT/'results/figures']:
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.name!='.gitkeep':manifest['files'].append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':digest(path)})
    (ROOT/'results/experiments/experiment_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'raw_and_prepared_data_unchanged':True,'paired_500_invoice_algorithm_checks':paired,'same_segment_comparison_cohort':True,'customer_assignments_aligned':True,'rendered_figures':len(figures),'final_test_scored':False},indent=2))

if __name__=='__main__':main()
