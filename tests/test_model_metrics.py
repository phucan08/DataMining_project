import unittest
import numpy as np,pandas as pd
from src.model_metrics import adjusted_rand,bitsets,decode_rules,item_count,masked_cases,pairwise_distances,recommend,rule_index,silhouette

class ModelMetricTests(unittest.TestCase):
    def test_rule_counts_include_empty_basket_in_denominator(self):
        baskets=[{'A','B'},{'A','C'},set()]
        frame=pd.DataFrame([{'antecedent':'A','consequent':'B','count_a':2,'count_b':1,'count_ab':1,'n_transactions':3}])
        rules=decode_rules(frame,baskets)
        self.assertAlmostEqual(rules.iloc[0]['support'],1/3)
        self.assertAlmostEqual(rules.iloc[0]['confidence'],.5)
        self.assertAlmostEqual(rules.iloc[0]['lift'],1.5)
        self.assertEqual(item_count(('A','missing'),bitsets(baskets)),0)
    def test_incorrect_engine_counts_are_rejected(self):
        frame=pd.DataFrame([{'antecedent':'A','consequent':'B','count_a':2,'count_b':1,'count_ab':2,'n_transactions':3}])
        with self.assertRaises(AssertionError):decode_rules(frame,[{'A','B'},{'A','C'},set()])
    def test_masks_are_stable_and_single_item_baskets_are_ineligible(self):
        cases=masked_cases(['1','2'],[{'A','new_product'},{'B'}],42)
        self.assertEqual(len(cases),1)
        self.assertEqual(cases,masked_cases(['1','2'],[{'new_product','A'},{'B'}],42))
        self.assertNotIn(cases[0][2],cases[0][1])
    def test_recommendations_exclude_seen_items_and_use_same_fallback(self):
        rules=pd.DataFrame([{'A':('A',),'B':('B',),'confidence':.8,'lift':2.,'count_ab':8}])
        items,used=recommend({'A'},rule_index(rules),['A','C','B','D'],3)
        self.assertEqual(items,['B','C','D']);self.assertTrue(used)
    def test_silhouette_matches_hand_computation(self):
        values=np.array([[0.],[1.],[10.],[11.]])
        distances=pairwise_distances(values)
        expected=np.mean([(10.5-1)/10.5,(9.5-1)/9.5,(9.5-1)/9.5,(10.5-1)/10.5])
        self.assertAlmostEqual(silhouette(distances,np.array([0,0,1,1])),expected)
    def test_ari_ignores_label_names_and_detects_disagreement(self):
        a=np.array([0,0,1,1])
        self.assertAlmostEqual(adjusted_rand(a,np.array([7,7,3,3])),1.)
        self.assertAlmostEqual(adjusted_rand(a,np.array([0,1,0,1])),-.5)

if __name__=='__main__':unittest.main()
