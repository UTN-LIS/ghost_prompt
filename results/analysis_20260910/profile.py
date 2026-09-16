from pathlib import Path
import pandas as pd
import io, json
root=Path(__file__).parent
raw=root.parent/'sheet_build_data'
for name in ['branching','previous']:
    parts=(root/f'source_{name}.txt').read_text().split('\f')
    for i,part in enumerate(parts):
        df=pd.read_csv(io.StringIO(part),index_col=0)
        print(name,i,df.shape)
        if 'task_id' in df:
            print('tasks',df.task_id.nunique(),'missing task',df.task_id.isna().sum())
            for c in ['dataset','method','model_name','passed','group','semantic_score']:
                if c in df: print(c,df[c].value_counts(dropna=False).head(8).to_dict())
        df.to_csv(root/f'{name}_{i}.csv',index=False)
print('raw schemas')
for n in ['lookaheads','branches','baselines','selections']:
    data=[json.loads(l) for l in (raw/f'{n}.jsonl').read_text().splitlines()]
    print(n,len(data),list(data[0]))
