import tempfile,unittest
from pathlib import Path
import pandas as pd
from src.final_evaluation import bootstrap_hit_rates,digest,score_cases,summarize,verify_records


class FinalEvaluationTests(unittest.TestCase):
    def test_freeze_rejects_modified_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model';path.write_text('original')
            records=[{'path':'model','sha256':digest(path)}]
            verify_records(directory,records);path.write_text('changed')
            with self.assertRaises(RuntimeError):verify_records(directory,records)

    def test_unseen_target_stays_in_denominator_and_precision_uses_fixed_k(self):
        frame=score_cases([('a',{'A'},'new')],{'a':('C1','Segment_1')},{},['A','B'],'popularity','all',5)
        metrics=summarize(frame,5)
        self.assertEqual(metrics['eligible_baskets'],1)
        self.assertEqual(metrics['hidden_targets_outside_train_vocabulary'],1)
        self.assertEqual(metrics['short_recommendation_rate'],1)
        self.assertEqual(metrics['zero_rule_fallback_rate'],1)
        frame.loc[0,'hit']=1
        self.assertEqual(summarize(frame,5)['precision_at_5_fixed_denominator'],.2)

    def test_identical_paired_methods_have_zero_difference_under_cluster_bootstrap(self):
        records=[{'InvoiceNo':i,'bootstrap_unit':unit,'method':method,'hit':hit}
                 for i,unit,hit in [('1','C1',1),('2','C1',0),('3','C2',1)] for method in ['a','b']]
        names,values=bootstrap_hit_rates(pd.DataFrame(records),['a','b'],100,42)
        self.assertTrue((values[:,0]==values[:,1]).all())
        self.assertEqual(set(values[:,0]),{.5,2/3,1.})

    def test_bootstrap_refuses_different_method_cohorts(self):
        frame=pd.DataFrame([{'InvoiceNo':'1','bootstrap_unit':'C1','method':'a','hit':1},
                            {'InvoiceNo':'2','bootstrap_unit':'C2','method':'b','hit':1}])
        with self.assertRaises(ValueError):bootstrap_hit_rates(frame,['a','b'],10,42)


if __name__=='__main__':unittest.main()
