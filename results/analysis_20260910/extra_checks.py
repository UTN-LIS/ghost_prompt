import sys
sys.path.append('/private/tmp/ghost_stats_deps')
import json, numpy as np, pandas as pd
from scipy import stats, optimize
from pathlib import Path
R=Path(__file__).resolve().parent
raw=pd.DataFrame([json.loads(l) for l in (R.parent/'sheet_build_data/lookaheads.jsonl').read_text().splitlines()]);B=pd.read_csv(R/'branching_4.csv');P=pd.read_csv(R/'branching_2.csv').iloc[:,:6]
raw['short']=raw.branch_token_ids.map(len)<12
ordered=(raw.top1_token_id!=raw.same_run_top1_id)|(raw.top2_token_id!=raw.same_run_top2_id)
out={'ordered_pair_mismatches':raw.loc[ordered,['task_id','position','forced_rank','saved_pair_matches_same_run']].to_dict('records'),'short_by_selector':{},'shift_threshold_sensitivity':[]}
def edit(a,b):
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        cur=[i]
        for j,y in enumerate(b,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+int(x!=y)))
        prev=cur
    return prev[-1]
edit_error=[];mismatch_error=[];persistence_error=[]
for _,r in raw.iterrows():
    a=r.baseline_token_ids;b=r.branch_token_ids;n=max(len(a),len(b))
    dif=[(a[i] if i<len(a) else None)!=(b[i] if i<len(b) else None) for i in range(n)]
    edit_error.append(abs(edit(a,b)/n-r.normalized_edit_distance))
    mismatch_error.append(abs(sum(dif)/n-r.aligned_mismatch))
    persistence_error.append(abs(sum(dif[1:])/(n-1)-r.persistence_after_forced))
out['independent_metric_verification']={'positions':len(raw),'max_edit_error':max(edit_error),'max_mismatch_error':max(mismatch_error),'max_persistence_error':max(persistence_error)}
for s,g in P.merge(raw[['task_id','position','short']],on=['task_id','position']).groupby('selector'):
    out['short_by_selector'][s]={'n_short':int(g.short.sum()),'short_passes':int(g.loc[g.short,'branch_passed'].sum())}
for a,d in [(.75,.25),(.8,.3),(.9,.3),(.8,.4)]:
    f=(raw.aligned_mismatch>=a)&(raw.normalized_edit_distance<=d)
    out['shift_threshold_sensitivity'].append(dict(mismatch_min=a,edit_max=d,n=int(f.sum()),fraction=f.mean()))
# Exploratory length-adjusted logistic association, separately for each benchmark.
out['length_adjusted_logit']=[]
for part,label in [(0,'HumanEval'),(1,'MBPP')]:
    D=pd.read_csv(R/f'previous_{part}.csv');y=(~D.passed.astype(bool)).astype(float).values
    for f in ['mean_entropy','min_margin']:
        F=np.column_stack([D[f],np.log1p(D.output_tokens)])
        sd=F.std(axis=0);Z=(F-F.mean(axis=0))/sd;X=np.column_stack([np.ones(len(D)),Z])
        def loss(b):return np.logaddexp(0,X@b).sum()-y@(X@b)
        def jac(b):return X.T@(1/(1+np.exp(-X@b))-y)
        res=optimize.minimize(loss,np.zeros(3),jac=jac,method='BFGS',options={'gtol':1e-7})
        prob=1/(1+np.exp(-X@res.x));H=X.T@((prob*(1-prob))[:,None]*X);cov=np.linalg.inv(H);se=np.sqrt(np.diag(cov));z=res.x/se
        out['length_adjusted_logit'].append(dict(dataset=label,feature=f,odds_ratio_per_sd=float(np.exp(res.x[1])),wald95=np.exp(res.x[1]+np.array([-1,1])*1.96*se[1]).tolist(),p_wald=float(2*stats.norm.sf(abs(z[1]))),gradient_max=float(abs(jac(res.x)).max()),n=len(D),failures=int(y.sum()),sd=float(sd[0])))
pv=np.array([x['p_wald'] for x in out['length_adjusted_logit']]);idx=np.argsort(pv);adj=np.maximum.accumulate(pv[idx]*(4-np.arange(4)))
for i,p in zip(idx,adj):out['length_adjusted_logit'][i]['p_holm_4']=float(min(p,1))
(R/'extra_checks.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));print(json.dumps(out,indent=2,ensure_ascii=False))
