import sys
sys.path.append('/private/tmp/ghost_stats_deps')
import pandas as pd, numpy as np
from scipy import stats
import json, io, itertools, math
from pathlib import Path
R=Path(__file__).resolve().parent;RAW=R.parent/'sheet_build_data'
B=pd.read_csv(R/'branching_4.csv');P=pd.read_csv(R/'branching_2.csv').iloc[:,:6]
Y=pd.read_csv(R/'problem_outcomes.csv',index_col=0)
lr=pd.DataFrame([json.loads(l) for l in (RAW/'lookaheads.jsonl').read_text().splitlines()]);br=pd.DataFrame([json.loads(l) for l in (RAW/'branches.jsonl').read_text().splitlines()])
base=pd.DataFrame([json.loads(l) for l in (RAW/'baselines.jsonl').read_text().splitlines()]);key=['task_id','position']
z=B.merge(br,on=key,suffixes=('_d','_r')); diff=z[z.code_d!=z.code_r]
print('Code differences',len(diff));print([(r.task_id,r.position,repr(r.code_d[:90]),repr(r.code_r[:90]),len(r.code_d),len(r.code_r)) for _,r in diff.head(4).iterrows()])
print('normalized code equality',all(a.replace('\r\n','\n').rstrip()==b.replace('\r\n','\n').rstrip() for a,b in zip(z.code_d,z.code_r)))
random_curve=[]
for k in range(1,6):
    m=P[P.selector=='Aleatorio'].groupby('task_id').branch_passed.sum()
    prob=[1-(math.comb(5-int(x),k) if 5-int(x)>=k else 0)/math.comb(5,k) for x in m]
    random_curve.append(dict(k=k,expected_recovered=sum(prob),expected_rate=np.mean(prob)))
obj=json.loads((R/'branch_results.json').read_text())
def cp(x,n,alpha=.025):
    return [0 if x==0 else stats.beta.ppf(alpha/2,x,n-x+1),1 if x==n else stats.beta.ppf(1-alpha/2,x+1,n-x)]
for pair in obj['paired']:
    w=cp(pair['a_only'],20);l=cp(pair['b_only'],20)
    pair['difference_conservative95']=[w[0]-l[1],w[1]-l[0]]
# Exact conditional label permutation for omnibus Q: enumerate all rows with nonconstant outcomes.
A=Y.values;n,k=A.shape;rs=A.sum(1);tot=A.sum();den=k*tot-(rs**2).sum()
options=[];constant=np.zeros(k,int)
for row in A:
    r=int(row.sum())
    if r==k:constant+=1
    elif r:
        opts=[]
        for idx in itertools.combinations(range(k),r):
            v=np.zeros(k,int);v[list(idx)]=1;opts.append(v)
        options.append(opts)
qn=lambda c:(k-1)*(k*(c*c).sum()-tot*tot)/den
q=qn(A.sum(0));dist=[qn(constant+sum(x)) for x in itertools.product(*options)]
obj['omnibus']['exact_conditional_p']=sum(x>=q-1e-12 for x in dist)/len(dist);obj['omnibus']['exact_permutations']=len(dist)
obj['random_curve_randomized_order_expectation']=random_curve
obj['audit']['code_difference_rows']=len(diff)
obj['audit']['code_matches_after_rstrip']=bool(all(a.replace('\r\n','\n').rstrip()==b.replace('\r\n','\n').rstrip() for a,b in zip(z.code_d,z.code_r)))
obj['audit']['rank_inconsistency_rows']=lr[lr.forced_rank!=2][key+['top1_token','top2_token','forced_rank','saved_pair_matches_same_run']].to_dict('records')
obj['audit']['baseline_failure_excluded'] =base[(~base.passed)&(~base.task_id.isin(Y.index))][['task_id','error']].to_dict('records')
obj['audit']['at_token_cap_tasks']=base[base.token_ids.map(len)==256].task_id.tolist()
# Unknown labels remain unknown in post-hoc selectors: bounds, not imputed failures.
results=[]
for f in ['normalized_edit_distance','anchor_score','weighted_semantic_divergence']:
    known=0;unknown_tasks=0;unknown_positions=0
    for t,g in lr.groupby('task_id'):
        top=g.sort_values([f,'position'],ascending=[False,True]).head(5)
        q=top.merge(B[key+['passed']],on=key,how='left')
        success=q.passed.eq(1).any();known+=int(success)
        unknown_tasks+=int(not success and q.passed.isna().any());unknown_positions+=int(q.passed.isna().sum())
    results.append(dict(feature=f,known_recovered=known,max_possible_recovered=known+unknown_tasks,missing_positions=unknown_positions))
obj['posthoc_selector_bounds']=results
(R/'branch_results.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)))
print(json.dumps({k:obj[k] for k in ['omnibus','random_curve_randomized_order_expectation','posthoc_selector_bounds']},indent=2))
