"""Run bounded-resource Weka fits; log failures instead of reporting partial models."""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
JAVA=Path(os.environ.get('JAVA_EXE','D:/java 25/bin/java.exe'))
JAVAC=JAVA.with_name('javac.exe')
JAR=Path(os.environ.get('WEKA_JAR','D:/Weka-3-8-7/weka.jar'))
CP=str(ROOT/'build/java')+os.pathsep+str(JAR)

def command(mode, *args):
    return [str(JAVA),'-Xmx2g','-cp',CP,'WekaExperimentBridge',mode,*map(str,args)]

def main():
    (ROOT/'build/java').mkdir(parents=True,exist_ok=True)
    subprocess.run([str(JAVAC),'-encoding','UTF-8','-cp',str(JAR),'-d',str(ROOT/'build/java'),str(ROOT/'src/WekaExperimentBridge.java')],check=True)
    protocol=json.loads((ROOT/'configs/experiment_protocol.json').read_text())
    output=ROOT/'results/experiments/global_rules';output.mkdir(parents=True,exist_ok=True)
    rows=[]
    inputs=ROOT/'results/experiments/inputs'
    for support in protocol['rules']['requested_min_support_grid']:
        support_index=protocol['rules']['requested_min_support_grid'].index(support)
        for algorithm in ['fpgrowth','apriori']:
            (output/f'{algorithm}_s{support_index}_rules.csv').unlink(missing_ok=True)
            for repeat in range(protocol['rules']['benchmark_repeats']):
                directory=output/f'{algorithm}_support{support}_rep{repeat}';directory.mkdir(parents=True,exist_ok=True)
                args=command('rules',inputs/'product_codes.txt',inputs/'train_transactions.txt',directory,support,1,algorithm+'_only')
                started=time.perf_counter()
                try:
                    with (directory/'console.log').open('w',encoding='utf-8') as stream:
                        subprocess.run(args,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=protocol['rules']['per_fit_wall_timeout_seconds'])
                    fit=pd.read_csv(directory/'benchmark.csv').iloc[0].to_dict()
                    fit.update({'repeat':repeat,'status':'completed','rules_path':str((directory/f'{algorithm}_s0_rules.csv').relative_to(ROOT))})
                    if repeat==0:
                        (output/f'{algorithm}_s{support_index}_rules.csv').write_bytes((directory/f'{algorithm}_s0_rules.csv').read_bytes())
                    rows.append(fit)
                    print(f'{algorithm} support={support} repeat={repeat}: completed',flush=True)
                except subprocess.TimeoutExpired:
                    rows.append({'algorithm':algorithm,'requested_support':support,'repeat':repeat,'status':'timeout','wall_seconds':time.perf_counter()-started,'rules_path':''})
                    print(f'{algorithm} support={support}: TIMEOUT; partial results ignored',flush=True)
                    break
                pd.DataFrame(rows).to_csv(output/'benchmark_status.csv',index=False)
    pd.DataFrame(rows).to_csv(output/'benchmark_status.csv',index=False)
    output=ROOT/'results/experiments/kmeans';output.mkdir(parents=True,exist_ok=True)
    with (output/'console.log').open('w',encoding='utf-8') as stream:
        subprocess.run(command('clusters',ROOT/'data/processed/rfm_train_features.csv',output,protocol['clustering']['starts_per_seed']),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=300)
    print('K-means grid completed',flush=True)

if __name__=='__main__':main()
