"""Export frozen train-only inputs and a deterministic matched benchmark subset."""
from pathlib import Path
import json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def main():
    output=ROOT/'results/experiments/inputs';output.mkdir(parents=True,exist_ok=True)
    catalog=pd.read_csv(ROOT/'data/processed/product_catalog_train.csv',dtype={'StockCode':'string'})
    (output/'product_codes.txt').write_text('\n'.join(catalog['StockCode'])+'\n',encoding='utf-8')
    with np.load(ROOT/'data/processed/basket_train_coordinates.npz') as matrix:
        rows=[[] for _ in range(int(matrix['shape'][0]))]
        for r,c in zip(matrix['row_indices'],matrix['column_indices']):rows[int(r)].append(int(c))
    text=[' '.join(str(item) for item in sorted(row)) for row in rows]
    (output/'train_transactions.txt').write_text('\n'.join(text)+'\n',encoding='utf-8')
    indices=np.sort(np.random.default_rng(42).choice(len(rows),size=500,replace=False))
    (output/'paired_subset_transactions.txt').write_text('\n'.join(text[i] for i in indices)+'\n',encoding='utf-8')
    (output/'paired_subset_row_indices.json').write_text(json.dumps(indices.tolist())+'\n')
    features=pd.read_csv(ROOT/'data/processed/rfm_train_features.csv',dtype={'CustomerID':'string'})
    header='@relation rfm_train_log_z\n\n'+''.join('@attribute '+name+' numeric\n' for name in features.columns[1:])+'\n@data\n'
    (output/'rfm_train_features.arff').write_text(header+features.iloc[:,1:].to_csv(index=False,header=False),encoding='utf-8')
    print(json.dumps({'train_baskets':len(rows),'product_vocabulary':len(catalog),'rfm_customers':len(features)}))
if __name__=='__main__':main()
