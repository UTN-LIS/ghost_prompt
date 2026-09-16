import sys, json
sys.path.append('/private/tmp/ghost_stats_deps')
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT=Path(__file__).resolve().parent
NEW=ROOT/'aligned_validation'
OLD=ROOT.parent/'sheet_build_data'
rng=np.random.default_rng(20260910)

def jsonl(path):
    return pd.DataFrame([json.loads(x) for x in path.read_text().splitlines()])

def wilson(x,n):
    z=stats.norm.ppf(.975); p=x/n; d=1+z*z/n
    m=(p+z*z/(2*n))/d
    h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [float(m-h),float(m+h)]

def bci(v,B=50000):
    v=np.asarray(v,float)
    z=v[rng.integers(len(v),size=(B,len(v)))].mean(1)
    return np.quantile(z,[.025,.975]).tolist()

def paired(a,b):
    a=np.asarray(a,bool); b=np.asarray(b,bool)
    w=int((a&~b).sum()); l=int((~a&b).sum())
    return {'a_only':w,'b_only':l,'both':int((a&b).sum()),
            'neither':int((~a&~b).sum()),
            'difference':float(a.mean()-b.mean()),
            'bootstrap95':bci(a.astype(int)-b.astype(int)),
            'p_exact':float(stats.binomtest(w,w+l).pvalue) if w+l else 1.0}

P=pd.read_csv(NEW/'aligned_positions.csv')
S=jsonl(NEW/'aligned_selections.jsonl')
B=jsonl(NEW/'aligned_branches.jsonl')
REP=json.loads((NEW/'aligned_report.json').read_text())
oldB=jsonl(OLD/'branches.jsonl')
oldS=jsonl(OLD/'selections.jsonl')
oldL=jsonl(OLD/'lookaheads.jsonl')
tasks=list(REP['task_results']); key=['task_id','position']

audit={'positions':len(P),'tasks':P.task_id.nunique(),'branches':len(B),
       'selections':len(S),'position_duplicates':int(P.duplicated(key).sum()),
       'branch_duplicates':int(B.duplicated(key).sum()),
       'selected_positions':int(P.selected_by_aligned_semantic.sum()),
       'reused_branches':int(B.reused_from_previous_validation.sum()),
       'new_branches':int((~B.reused_from_previous_validation).sum())}
assert len(P)==1649 and P.task_id.nunique()==20 and not P.duplicated(key).any()
assert len(B)==100 and B.task_id.nunique()==20 and not B.duplicated(key).any()
assert len(S)==20 and audit['selected_positions']==100
assert (B.groupby('task_id').size()==5).all()
assert set(map(tuple,P.loc[P.selected_by_aligned_semantic,key].values)) == set(map(tuple,B[key].values))

# Reconstruct the aligned score from tie-aware within-task percentile ranks.
features=['aligned_persistence','aligned_weighted_divergence','anchor_score']
parts=[P.groupby('task_id')[f].transform(lambda x:(x.rank(method='average')-1)/max(len(x)-1,1)) for f in features]
P['score_recomputed']=np.mean(parts,axis=0)
audit['score_max_abs_error']=float(abs(P.aligned_semantic_score-P.score_recomputed).max())
audit['score_rows_different_at_1e_12']=int(abs(P.aligned_semantic_score-P.score_recomputed).gt(1e-12).sum())
# Ten rows differ slightly, consistent with ties resolved from greater upstream
# precision than retained in the CSV. Validate selection separately below.
assert audit['score_max_abs_error']<0.004

# Validate top-five selections and report outcomes.
for _,r in S.iterrows():
    selected=set(r.aligned_semantic_positions)
    assert selected==set(P[(P.task_id==r.task_id)&P.selected_by_aligned_semantic].position)
    g=P[P.task_id==r.task_id]
    cutoff=g[g.position.isin(selected)].aligned_semantic_score.min()
    assert not (g[~g.position.isin(selected)].aligned_semantic_score>cutoff+1e-12).any()
Ynew=B.groupby('task_id').passed.max().reindex(tasks).astype(bool)
assert Ynew.to_dict()==REP['task_results'] and int(Ynew.sum())==10

# Recover old semantic and frozen comparator outcomes.
old_sem={(r.task_id,p) for _,r in oldS.iterrows() for p in r.by_selector['semantic_lookahead']}
q=oldB[[tuple(x) in old_sem for x in oldB[key].itertuples(index=False,name=None)]]
Yold=q.groupby('task_id').passed.max().reindex(tasks,fill_value=False).astype(bool)
Y={'aligned_semantic':Ynew}
comparisons={'aligned_vs_old_semantic':paired(Ynew,Yold)}
for name in ['entropy','probability_margin','random']:
    wanted={(r.task_id,p) for _,r in oldS.iterrows() for p in r.by_selector[name]}
    q=oldB[[tuple(x) in wanted for x in oldB[key].itertuples(index=False,name=None)]]
    Y[name]=q.groupby('task_id').passed.max().reindex(tasks,fill_value=False).astype(bool)
    comparisons['aligned_vs_'+name]=paired(Ynew,Y[name])
names=['aligned_vs_entropy','aligned_vs_probability_margin','aligned_vs_random']
p=np.array([comparisons[n]['p_exact'] for n in names]); order=np.argsort(p)
adj=np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p))))
out=np.empty(len(p)); out[order]=np.minimum(adj,1)
for n,v in zip(names,out): comparisons[n]['p_holm_3']=float(v)

# Changes to selected positions and branches.
overlap=[]
for _,r in S.iterrows():
    a=set(r.aligned_semantic_positions); o=set(r.old_semantic_positions)
    overlap.append({'task_id':r.task_id,'intersection':len(a&o),
                    'jaccard':len(a&o)/len(a|o),
                    'new_positions':sorted(a-o),'dropped_positions':sorted(o-a)})
oldkeys=set(map(tuple,oldB[key].values)); newkeys=set(map(tuple,B[key].values))
new_only=B[[tuple(x) not in oldkeys for x in B[key].itertuples(index=False,name=None)]]
dropped=oldB[[tuple(x) in old_sem and tuple(x) not in newkeys for x in oldB[key].itertuples(index=False,name=None)]]

counts=B.groupby('task_id').passed.sum().reindex(tasks)
summary={'recovered':int(Ynew.sum()),'rate':float(Ynew.mean()),
         'wilson95':wilson(Ynew.sum(),len(Ynew)),
         'passing_branches':int(B.passed.sum()),
         'branch_precision':float(B.passed.mean()),
         'branch_precision_cluster_bootstrap95':bci(counts/5),
         'reused':audit['reused_branches'],'newly_generated':audit['new_branches'],
         'generation_seconds_recorded':float(B.generation_latency_s.sum()),
         'new_generation_seconds_recorded':float(B.loc[~B.reused_from_previous_validation,'generation_latency_s'].sum())}

# Budget curve in the selector's saved ranking order.
rows=[]
for _,r in S.iterrows():
    lookup=B[B.task_id==r.task_id].set_index('position').passed.to_dict()
    for rank,pos in enumerate(r.aligned_semantic_positions,1):
        rows.append({'task_id':r.task_id,'rank':rank,'position':pos,'passed':bool(lookup[pos])})
Q=pd.DataFrame(rows); curve=[]
for k in range(1,6):
    z=Q[Q['rank']<=k].groupby('task_id').passed.max().reindex(tasks,fill_value=False)
    curve.append({'k':k,'recovered':int(z.sum()),'rate':float(z.mean()),'wilson95':wilson(z.sum(),len(z))})

selected=P[P.selected_by_aligned_semantic].merge(B[key+['passed']],on=key)
shift={'all':{'n':int(P.shift_detected.sum()),'rate':float(P.shift_detected.mean())},
       'selected':{'n':int(selected.shift_detected.sum()),
                   'rate':float(selected.shift_detected.mean()),
                   'passes':int(selected.loc[selected.shift_detected,'passed'].sum())}}
for old,new in [('persistence_after_forced','aligned_persistence'),
                ('weighted_semantic_divergence','aligned_weighted_divergence')]:
    P[new+'_delta_old']=P[new]-P[old]
shift['metric_changes']={new:{
    'mean_delta':float(P[new+'_delta_old'].mean()),
    'median_delta':float(P[new+'_delta_old'].median()),
    'changed_fraction':float(P[new+'_delta_old'].abs().gt(1e-12).mean()),
    'mean_delta_shift_detected':float(P.loc[P.shift_detected,new+'_delta_old'].mean()),
    'mean_delta_no_shift':float(P.loc[~P.shift_detected,new+'_delta_old'].mean())}
    for new in ['aligned_persistence','aligned_weighted_divergence']}

# Old score, reconstructed from the same original records.
oldparts=[oldL.groupby('task_id')[f].transform(lambda x:(x.rank(method='average')-1)/(len(x)-1))
          for f in ['persistence_after_forced','weighted_semantic_divergence','anchor_score']]
oldL['old_score']=np.mean(oldparts,axis=0)
M=P.merge(oldL[key+['old_score']],on=key,validate='one_to_one')
M=M.merge(oldL[key+['entropy','probability_margin']],on=key,validate='one_to_one')
correlations={'aligned_vs_old_score_spearman':float(stats.spearmanr(M.aligned_semantic_score,M.old_score).statistic),
              'aligned_vs_entropy_spearman':float(stats.spearmanr(M.aligned_semantic_score,M.entropy).statistic),
              'aligned_vs_margin_spearman':float(stats.spearmanr(M.aligned_semantic_score,M.probability_margin).statistic)}

audit['computed_overlap_mean']=float(np.mean([x['intersection'] for x in overlap]))
assert abs(audit['computed_overlap_mean']-REP['mean_top5_overlap_with_old_selector'])<1e-12
assert int(P.shift_detected.sum())==REP['shift_affected_positions']
result={'audit':audit,'summary':summary,'comparisons':comparisons,
        'same_recovered_tasks_as_old':bool(Ynew.equals(Yold)),
        'old_semantic_recovered':int(Yold.sum()),'curve':curve,
        'overlap':{'total_intersection':sum(x['intersection'] for x in overlap),
                   'mean_per_task':audit['computed_overlap_mean'],
                   'mean_jaccard':float(np.mean([x['jaccard'] for x in overlap])),
                   'details':overlap},
        'changed_branches':{'new_only':len(new_only),'new_only_passes':int(new_only.passed.sum()),
                            'dropped':len(dropped),'dropped_passes':int(dropped.passed.sum())},
        'shift':shift,'correlations':correlations}
(ROOT/'aligned_results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps(result,indent=2,ensure_ascii=False))
