from pathlib import Path
import subprocess
from run_weka_fits import command,ROOT

if __name__=='__main__':
    inputs=ROOT/'results/experiments/inputs';output=ROOT/'results/experiments/paired_subset_rules';output.mkdir(parents=True,exist_ok=True)
    with (output/'console.log').open('w',encoding='utf-8') as stream:
        subprocess.run(command('rules',inputs/'product_codes.txt',inputs/'paired_subset_transactions.txt',output,'0.02,0.05',3),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=180)
    print('Matched subset benchmark completed')
