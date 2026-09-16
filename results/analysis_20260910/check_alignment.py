import json, keyword, ast
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'sheet_build_data'
P=pd.read_csv(ROOT/'aligned_validation/aligned_positions.csv')
L=pd.DataFrame([json.loads(x) for x in (OLD/'lookaheads.jsonl').read_text().splitlines()])
BASE=pd.DataFrame([json.loads(x) for x in (OLD/'baselines.jsonl').read_text().splitlines()]).set_index('task_id')

def token_class(text):
    if not text:return 'empty'
    if text.isspace() or '\n' in text:return 'whitespace'
    s=text.strip()
    if keyword.iskeyword(s):return 'keyword'
    if s.isidentifier():return 'identifier'
    if s in {'+','-','*','/','//','%','**','=','==','!=','<','>','<=','>=',':=','&','|','^','~','<<','>>','->'}:return 'operator'
    try:ast.literal_eval(s);return 'literal'
    except Exception:return 'other'

def weight(a,b):
    if a==b:return 0.
    c={token_class(a),token_class(b)}
    if c=={'whitespace'}:return 0.
    if c=={'identifier'}:return .2
    if 'whitespace' in c:return .25
    if c & {'keyword','operator','literal'}:return 1.
    return .5

def align(a,b,priority):
    n,m=len(a),len(b);d=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1):d[i][0]=i
    for j in range(m+1):d[0][j]=j
    for i in range(1,n+1):
        for j in range(1,m+1):d[i][j]=min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]!=b[j-1]))
    out=[];i=n;j=m
    while i or j:
        opts={}
        if i and j and d[i][j]==d[i-1][j-1]+(a[i-1]!=b[j-1]):opts['diag']=(a[i-1],b[j-1],i-1,j-1)
        if i and d[i][j]==d[i-1][j]+1:opts['del']=(a[i-1],None,i-1,j)
        if j and d[i][j]==d[i][j-1]+1:opts['ins']=(None,b[j-1],i,j-1)
        op=next(x for x in priority if x in opts);x,y,i,j=opts[op];out.append((x,y))
    return out[::-1]

joined=P.merge(L,on=['task_id','position'],validate='one_to_one')
for priority in [('diag','del','ins'),('diag','ins','del'),('del','ins','diag'),('ins','del','diag')]:
    pe=[];we=[];shift=[]
    for _,r in joined.iterrows():
        a=r.baseline_token_ids[1:];b=r.branch_token_ids[1:]
        pairs=align(a,b,priority)
        # Aligned persistence is the unit-cost edit distance normalized by the
        # 11-token continuation length, not mismatches per alignment column.
        persist=sum((x is None) or (y is None) or (x!=y) for x,y in pairs)/max(len(a),len(b),1)
        base_trace=BASE.loc[r.task_id].trace
        amap={tid:None for tid in []}
        # Text is position-specific for baseline and sequence-specific for branch.
        at=[base_trace[r.position+i]['token_text'] for i in range(1,len(a)+1)]
        bt=r.branch_token_texts[1:]
        ai=bi=0;textpairs=[]
        for x,y in pairs:
            tx='' if x is None else at[ai]
            ty='' if y is None else bt[bi]
            textpairs.append((tx,ty))
            ai+=x is not None;bi+=y is not None
        div=sum(weight(x,y) for x,y in textpairs)/len(textpairs) if textpairs else 0
        pe.append(abs(persist-r.aligned_persistence));we.append(abs(div-r.aligned_weighted_divergence))
        shift.append(abs(persist-r.persistence_after_forced_x)>1e-12)
    print(priority,'persist max/count',max(pe),sum(x>1e-12 for x in pe),'div max/count',max(we),sum(x>1e-12 for x in we),'shift count',sum(shift),'shift mismatch',sum(a!=b for a,b in zip(shift,joined.shift_detected)))
