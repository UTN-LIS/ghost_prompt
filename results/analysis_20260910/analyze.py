"""Reproducible analysis of Drive snapshots; no model or generated code execution.
Run with bundled Python; optional scipy/matplotlib dependencies in /private/tmp/ghost_stats_deps.
"""
import sys, os
sys.path.append('/private/tmp/ghost_stats_deps')
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/ghost_stats_mpl')
from pathlib import Path
import io, json, math, hashlib, itertools, ast, re
import numpy as np
import pandas as pd
from scipy import stats
ROOT=Path(__file__).resolve().parent
RAW=ROOT.parent/'sheet_build_data'
SEED=20260910
rng=np.random.default_rng(SEED)
def readraw(name): return pd.DataFrame([json.loads(x) for x in (RAW/f'{name}.jsonl').read_text().splitlines()])
def loadpart(name,i): return pd.read_csv(io.StringIO((ROOT/f'source_{name}.txt').read_text().split('\f')[i]),index_col=0)
def dump(name,obj): (ROOT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)))
def wilson(x,n):
    z=stats.norm.ppf(.975); p=x/n; d=1+z*z/n
    mid=(p+z*z/(2*n))/d; half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [float(mid-half),float(mid+half)]
def adjust(p,method='holm'):
    p=np.array(p,float); order=np.argsort(p); m=len(p)
    a=np.maximum.accumulate(p[order]*(m-np.arange(m))) if method=='holm' else np.minimum.accumulate((p[order]*m/(np.arange(m)+1))[::-1])[::-1]
    out=np.empty(m);out[order]=np.minimum(a,1);return out
def bci(x,B=30000):
    x=np.asarray(x,float); vals=x[rng.integers(len(x),size=(B,len(x)))].mean(axis=1)
    return np.quantile(vals,[.025,.975]).tolist()
def paired(a,b):
    a=np.asarray(a,int);b=np.asarray(b,int); win=int(((a==1)&(b==0)).sum());loss=int(((a==0)&(b==1)).sum())
    return dict(a_only=win,b_only=loss,both=int(((a==1)&(b==1)).sum()),neither=int(((a==0)&(b==0)).sum()),difference=float((a-b).mean()),difference_bootstrap95=bci(a-b),p_exact=float(stats.binomtest(win,win+loss).pvalue) if win+loss else 1.)
B=loadpart('branching',4); L=loadpart('branching',5); P=loadpart('branching',2).iloc[:,:6]; T=loadpart('branching',3)
BR=readraw('branches');LR=readraw('lookaheads');BASE=readraw('baselines'); SEL=readraw('selections')
key=['task_id','position']; names=['Semántico','Entropía','Margen','Aleatorio']; rawname=dict(zip(names,['semantic_lookahead','entropy','probability_margin','random']))
audit={'seed':SEED,'drive_branch_rows':len(B),'drive_lookaheads':len(L),'budget_rows':len(P),'problems':P.task_id.nunique(),'branch_duplicates':int(B.duplicated(key).sum()),'lookahead_duplicates':int(L.duplicated(key).sum()),'missing_semantic_score_lookahead':int(L.semantic_score.isna().sum()),'unevaluated':int((L.full_branch_evaluated==0).sum()),'missing_outcome_evaluated':int(L.loc[L.full_branch_evaluated==1,'branch_passed'].isna().sum()),'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['source_branching.txt','source_previous.txt','source_bitacora.txt']}}
assert not B.duplicated(key).any() and not L.duplicated(key).any()
assert L.loc[L.full_branch_evaluated==0,'branch_passed'].isna().all()
assert set(map(tuple,B[key].values))==set(map(tuple,L.loc[L.full_branch_evaluated==1,key].values))
for left,right,cols in [(B,BR,['passed','entropy','probability_margin']),(L,LR,['entropy','probability_margin'])]:
    m=left.merge(right,on=key,suffixes=('_drive','_raw'),validate='one_to_one'); assert len(m)==len(left)
    for c in cols: assert np.allclose(m[c+'_drive'],m[c+'_raw'],rtol=1e-12,atol=1e-12)
audit['local_raw_matches_drive_numeric_and_keys']=True
audit['branch_code_exact_matches_raw']=bool((B.merge(BR,on=key,suffixes=('_d','_r')).code_d==B.merge(BR,on=key,suffixes=('_d','_r')).code_r).all())
for c,rc in [('persistence','persistence_after_forced'),('semantic_divergence','weighted_semantic_divergence'),('anchor_score','anchor_score')]:
    m=L.merge(LR,on=key,suffixes=('_d','_r'))
    assert np.allclose(m[c+'_d' if c==rc else c],m[rc+'_r' if c==rc else rc])
# Rebuild frozen score using within-task midranks, no outcome labels.
features=['persistence_after_forced','weighted_semantic_divergence','anchor_score']
LR['score_recomputed']=np.mean([LR.groupby('task_id')[f].transform(lambda s:(s.rank(method='average')-1)/(len(s)-1)) for f in features],axis=0)
m=B.merge(LR[key+['score_recomputed']],on=key,validate='one_to_one')
audit['score_max_abs_error']=float(abs(m.semantic_score-m.score_recomputed).max());assert audit['score_max_abs_error']<1e-12
L=L.drop(columns='semantic_score').merge(LR,on=key,suffixes=('_drive',''),validate='one_to_one')
joined=P.merge(B[key+['passed']],on=key,validate='many_to_one')
assert (joined.branch_passed==joined.passed).all()
assert (P.groupby(['task_id','selector']).size()==5).all()
for _,g in P.groupby(['task_id','selector']):
    g=g.sort_values('rank');assert list(g['rank'])==list(range(1,6));assert np.array_equal(g.branch_passed.cummax(),g.recovered_within_k)
for _,s in SEL.iterrows():
    for n in names: assert P[(P.task_id==s.task_id)&(P.selector==n)].sort_values('rank').position.tolist()==s.by_selector[rawname[n]]
tasks=sorted(P.task_id.unique()); Y=P.groupby(['task_id','selector']).branch_passed.max().unstack()[names].loc[tasks]
curves=[];summary=[]
for n in names:
    q=P[P.selector==n]; cnt=q.groupby('task_id').branch_passed.sum().reindex(tasks)
    selcol={'Semántico':'sel_semantic','Entropía':'sel_entropy','Margen':'sel_margin','Aleatorio':'sel_random'}[n]
    selected=B[B[selcol]==1]
    fullseconds=float(selected.latency_s.sum()); lookseconds=float(LR.lookahead_latency_s.sum()) if n=='Semántico' else 0.
    summary.append(dict(selector=n,recovered=int(Y[n].sum()),n=len(tasks),rate=Y[n].mean(),wilson95=wilson(Y[n].sum(),len(tasks)),branch_passes=int(cnt.sum()),nominal_branches=len(q),branch_precision=cnt.mean()/5,branch_precision_cluster_bootstrap95=bci(cnt/5),full_generation_s=fullseconds,lookahead_s=lookseconds,total_generation_s=fullseconds+lookseconds,full_seconds_per_recovery=fullseconds/Y[n].sum(),total_seconds_per_recovery=(fullseconds+lookseconds)/Y[n].sum()))
    for k in range(1,6):
        z=q[q['rank']<=k].groupby('task_id').branch_passed.max().reindex(tasks)
        curves.append(dict(selector=n,k=k,recovered=int(z.sum()),rate=z.mean(),wilson95=wilson(z.sum(),len(tasks))))
pairs=[]
for a,b in itertools.combinations(names,2):pairs.append(dict(a=a,b=b,**paired(Y[a],Y[b])))
for v,p in zip(pairs,adjust([r['p_exact'] for r in pairs])):v['p_holm_6']=p
# One omnibus paired permutation test: exchange selector labels within each problem.
mat=Y.values; col=mat.sum(0); rsum=mat.sum(1); total=mat.sum(); den=4*total-(rsum**2).sum()
qobs=3*(4*(col**2).sum()-total**2)/den
count=0;N=50000
for _ in range(50):
    order=np.argsort(rng.random((1000,len(tasks),4)),axis=2)
    perm=np.take_along_axis(np.broadcast_to(mat,(1000,*mat.shape)),order,axis=2)
    sums=perm.sum(1);qperm=3*(4*(sums**2).sum(1)-total**2)/den
    count+=int((qperm>=qobs-1e-12).sum())
omnibus=dict(cochran_q=float(qobs),p_chi2=float(stats.chi2.sf(qobs,3)),permutation_p=(count+1)/(N+1),permutations=N)
overlap=[]
for a,b in itertools.combinations(names,2):
    rows=[]
    for t in tasks:
        aa=set(P[(P.task_id==t)&(P.selector==a)].position);bb=set(P[(P.task_id==t)&(P.selector==b)].position)
        rows.append(dict(task=t,intersection=len(aa&bb),jaccard=len(aa&bb)/len(aa|bb),union=len(aa|bb)))
    overlap.append(dict(a=a,b=b,total_intersection=sum(x['intersection'] for x in rows),mean_jaccard=np.mean([x['jaccard'] for x in rows]),union_budget=sum(x['union'] for x in rows),recovered_union=int((Y[a]|Y[b]).sum()),a_exclusive=Y.index[(Y[a]==1)&(Y[b]==0)].tolist(),b_exclusive=Y.index[(Y[a]==0)&(Y[b]==1)].tolist()))
# Descriptive fixed-budget hybrid, newly proposed after seeing this dataset, not a validation result.
hybrid=[]
for t in tasks:
    e=P[(P.task_id==t)&(P.selector=='Entropía')].sort_values('rank').position.tolist()
    s=P[(P.task_id==t)&(P.selector=='Semántico')].sort_values('rank').position.tolist()
    positions=e[:2]
    for p in s+e:
        if p not in positions and len(positions)<5:positions.append(p)
    result=B[(B.task_id==t)&B.position.isin(positions)].passed.max()
    hybrid.append(dict(task_id=t,positions=positions,recovered=int(result)))
# Raw numerical consistency and practical sensitivity.
audit['saved_pair_mismatch_positions']=int((~LR.saved_pair_matches_same_run).sum())
audit['forced_rank_counts']=LR.forced_rank.value_counts().sort_index().to_dict()
audit['mismatch_tasks']=sorted(LR.loc[~LR.saved_pair_matches_same_run,'task_id'].unique())
audit['baseline_rows']=len(BASE);audit['baseline_failures']=int((~BASE.passed).sum());audit['baseline_at_token_cap']=int(BASE.token_ids.map(len).eq(256).sum())
audit['unique_pass_branches']=int(B.passed.sum());audit['union_recovered']=int(Y.max(axis=1).sum())
audit['duplicate_full_code_within_task']=int(B.duplicated(['task_id','code']).sum())
audit['lookahead_length_counts']=LR.branch_token_ids.map(len).value_counts().to_dict()
audit['rank_not_2_evaluated']=int(B.merge(LR[key+['forced_rank']],on=key).forced_rank.ne(2).sum())
audit['selected_tasks_at_token_cap']=int(BASE[BASE.task_id.isin(tasks)].token_ids.map(len).eq(256).sum())
audit['evaluated_branches_at_token_cap']=int(BR.token_ids.map(len).eq(256).sum())
safe=P.merge(LR[key+['forced_rank','saved_pair_matches_same_run']],on=key)
audit['recovery_if_only_consistent_top2']={n:int(g.assign(ok=g.branch_passed.astype(bool)&g.forced_rank.eq(2)&g.saved_pair_matches_same_run).groupby('task_id').ok.max().sum()) for n,g in safe.groupby('selector')}
# Quantify positional mismatch versus edit distance; a diagnostic proxy, not semantic equivalence.
LR['shift_gap']=LR.aligned_mismatch-LR.normalized_edit_distance
LR['shift_flag']=(LR.aligned_mismatch>=.8)&(LR.normalized_edit_distance<=.3)
shift={'definition':'aligned_mismatch >= 0.8 AND normalized_edit_distance <= 0.3; exploratory diagnostic only','n_flagged':int(LR.shift_flag.sum()),'fraction_flagged':LR.shift_flag.mean(),'mean_gap':LR.shift_gap.mean(),'median_gap':LR.shift_gap.median(),'fraction_any_positive_gap':LR.shift_gap.gt(1e-12).mean(),'by_selector':{}}
for n in names:
    q=P[P.selector==n].merge(LR[key+['shift_flag','shift_gap']],on=key)
    shift['by_selector'][n]=dict(flagged=int(q.shift_flag.sum()),n=len(q),flagged_passes=int(q.loc[q.shift_flag,'branch_passed'].sum()),mean_gap=q.shift_gap.mean())
ex=LR[(LR.task_id=='HumanEval/140')&LR.position.eq(4)].iloc[0]
shift['example']={c:ex[c] for c in ['task_id','position','baseline_snippet','branch_snippet','aligned_mismatch','normalized_edit_distance','persistence_after_forced','weighted_semantic_divergence','anchor_score','score_recomputed']}
LR[key+['shift_gap','shift_flag','score_recomputed']].to_csv(ROOT/'shift_diagnostics.csv',index=False)
# Spearman structure across all positions, with task-balanced summary.
fields=['entropy','probability_margin','persistence_after_forced','weighted_semantic_divergence','anchor_score','normalized_edit_distance','score_recomputed']
correlations=[]
for a,b in itertools.combinations(fields,2):
    within=[stats.spearmanr(g[a],g[b]).statistic for _,g in LR.groupby('task_id') if g[a].nunique()>1 and g[b].nunique()>1]
    correlations.append(dict(a=a,b=b,pooled_rho=stats.spearmanr(LR[a],LR[b]).statistic,median_within_task_rho=np.median(within),n_tasks=len(within)))
# Within-task discrimination restricted to evaluated positions; no full-oracle claims.
E=LR.merge(B[key+['passed']],on=key,validate='one_to_one')
directions={f:(-1 if f=='probability_margin' else 1) for f in fields}
associations=[]
def auc(a,y):
    a=np.asarray(a);y=np.asarray(y,bool); p=y.sum();n=(~y).sum()
    return float((stats.rankdata(a)[y].sum()-p*(p+1)/2)/(p*n)) if p and n else np.nan
for f in fields:
    vals=[]; weights=[]; per=[]
    for t,g in E.groupby('task_id'):
        v=auc(directions[f]*g[f].values,g.passed.values)
        if np.isfinite(v):vals.append(v);per.append({'task':t,'auc':v})
    associations.append(dict(feature=f,direction=directions[f],pooled_auc=auc(directions[f]*E[f].values,E.passed.values),macro_within_task_auc=float(np.mean(vals)),macro_task_bootstrap95=bci(vals),informative_tasks=len(vals),scope='selected full branches only; selection bias'))
# Failure categories, observed latencies, eligible position imbalance.
errors=B.loc[B.passed==0,'error'].fillna('missing').map(lambda x: next((v for v in ['Timeout','AssertionError','SyntaxError','IndentationError','NameError','TypeError','IndexError','KeyError','RecursionError','AttributeError'] if v.lower() in x.lower()),'Other'))
audit['failure_types']=errors.value_counts().to_dict();audit['eligible_positions_per_task']=LR.groupby('task_id').size().to_dict()
audit['lookahead_seconds_total']=float(LR.lookahead_latency_s.sum());audit['unique_full_generation_seconds_total']=float(B.latency_s.sum())
dump('branch_results.json',dict(audit=audit,summary=summary,paired=pairs,omnibus=omnibus,curves=curves,overlap=overlap,hybrid_exploratory=dict(recovered=sum(x['recovered'] for x in hybrid),n=20,rows=hybrid),shift=shift,correlations=correlations,associations=associations))
pd.DataFrame(summary).to_csv(ROOT/'selector_summary.csv',index=False);pd.DataFrame(pairs).to_csv(ROOT/'paired_comparisons.csv',index=False);pd.DataFrame(curves).to_csv(ROOT/'budget_curves.csv',index=False);Y.to_csv(ROOT/'problem_outcomes.csv')
# Prior observational datasets: separate strata, preselect interpretable metrics; FDR across all 16 tests.
prior=[]; prior_tests=[]
prior_features=['mean_entropy','max_entropy','mean_margin','min_margin','output_tokens','gen_time_s','entropy_std','code_lines']
for i,name in [(0,'HumanEval'),(1,'MBPP')]:
    D=loadpart('previous',i);D['failure']=~D.passed.astype(bool)
    prior.append(dict(dataset=name,n=len(D),tasks=D.task_id.nunique(),passed=int(D.passed.sum()),rate=float(D.passed.mean()),wilson95=wilson(D.passed.sum(),len(D)),duplicates=int(D.duplicated(['task_id','sample','method']).sum()),error_types=D.error_type.fillna('none').value_counts().to_dict(),model_names=D.model_name.unique().tolist() if 'model_name' in D else 'not recorded in sheet',missing_metrics=D[prior_features].isna().sum().to_dict()))
    for f in prior_features:
        v=pd.to_numeric(D[f],errors='coerce'); ok=v.notna(); v=v[ok]; y=D.failure[ok]
        fail=v[y];succ=v[~y];u=stats.mannwhitneyu(fail,succ,alternative='two-sided',method='asymptotic')
        a=auc(v,y); boot=[]
        for _ in range(4000):
            ix=rng.integers(len(v),size=len(v)); val=auc(v.values[ix],y.values[ix]);
            if np.isfinite(val):boot.append(val)
        prior_tests.append(dict(dataset=name,feature=f,n=len(v),mean_pass=succ.mean(),mean_fail=fail.mean(),median_pass=succ.median(),median_fail=fail.median(),auc_high_predicts_failure=a,auc_bootstrap95=np.quantile(boot,[.025,.975]).tolist(),rank_biserial=2*a-1,p_mannwhitney=u.pvalue,spearman_failure=stats.spearmanr(v,y.astype(int)).statistic))
for row,p in zip(prior_tests,adjust([x['p_mannwhitney'] for x in prior_tests],'bh')):row['q_bh_16']=p
dump('previous_results.json',dict(summary=prior,associations=prior_tests))
pd.DataFrame(prior_tests).to_csv(ROOT/'previous_associations.csv',index=False)
# Prospective planning under explicit effect/discordance assumptions, no post-hoc observed power.
power=[]
for delta,q in [(.20,.30),(.10,.30),(.20,.50)]:
    for n in [20,40,60,80,100,150,200,300]:
        draws=rng.multinomial(n,[(q+delta)/2,(q-delta)/2,1-q],size=30000);w=draws[:,0];l=draws[:,1];m=w+l
        pv=np.minimum(1.,2*stats.binom.cdf(np.minimum(w,l),m,.5)); power.append(dict(delta=delta,discordance=q,n=n,power=float((pv<.05).mean())))
dump('planning_scenarios.json',power)
print(json.dumps(dict(audit=audit,summary=summary,paired=pairs,omnibus=omnibus,shift=shift,prior_summary=prior,prior_tests=prior_tests),indent=2,ensure_ascii=False,default=str))
