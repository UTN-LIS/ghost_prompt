import sys,os,json
sys.path.append('/private/tmp/ghost_stats_deps')
os.environ['MPLCONFIGDIR']='/private/tmp/ghost_stats_mpl'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np,pandas as pd
from pathlib import Path
R=Path(__file__).resolve().parent
D=json.loads((R/'branch_results.json').read_text());PR=json.loads((R/'previous_results.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','savefig.facecolor':'white'})
colors={'Semántico':'#B65A22','Entropía':'#24669A','Margen':'#6A7632','Aleatorio':'#646464'}
markers={'Semántico':'o','Entropía':'s','Margen':'^','Aleatorio':'D'}
def save(fig,name):
    fig.savefig(R/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(R/(name+'.svg'),bbox_inches='tight');plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(12,5.2),gridspec_kw={'width_ratios':[1,1.15]})
ax=axes[0]
for i,r in enumerate(D['summary']):
    lo,hi=r['wilson95'];ax.errorbar(r['rate'],3-i,xerr=[[r['rate']-lo],[hi-r['rate']]],fmt=markers[r['selector']],color=colors[r['selector']],capsize=5,markersize=8,lw=2)
    ax.text(.78,3-i,f"{r['recovered']}/20",va='center')
ax.set_yticks(range(4),[r['selector'] for r in D['summary']][::-1]);ax.set_xlim(0,1);ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set_xlabel('Problemas recuperados · IC 95% Wilson');ax.set_title('Cinco ramas completas por problema',loc='left',pad=16);ax.grid(axis='x',alpha=.16)
ax=axes[1]
for n in colors:
    if n=='Aleatorio':
        rows=D['random_curve_randomized_order_expectation'];vals=[r['expected_rate'] for r in rows];label='Aleatorio: orden aleatorizado (esperado)';ls='--'
    else:
        rows=[r for r in D['curves'] if r['selector']==n];vals=[r['rate'] for r in rows];label=n;ls='-'
    ax.plot(range(1,6),vals,marker=markers[n],ls=ls,label=label,color=colors[n],lw=2)
ax.set_ylim(0,.65);ax.set_xticks(range(1,6));ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set_xlabel('Presupuesto de ramas completas (k)');ax.set_ylabel('Fracción de los 20 problemas');ax.set_title('Recuperación según presupuesto',loc='left',pad=16);ax.legend(fontsize=8.5,loc='upper left');ax.grid(alpha=.16)
fig.suptitle('Branching top-2 · Qwen2.5-Coder-7B · HumanEval base',x=.03,ha='left',fontsize=16,y=1.02)
fig.text(.03,-.06,'20 fallos elegibles del baseline. Curvas descriptivas; no prueban superioridad.\nLa curva aleatoria promedia todos los órdenes del conjunto aleatorio guardado; no es una nueva corrida.',fontsize=9,color='#444444')
fig.tight_layout(w_pad=2);save(fig,'01_recuperacion')
L=pd.DataFrame([json.loads(l) for l in (R.parent/'sheet_build_data/lookaheads.jsonl').read_text().splitlines()])
fig,axes=plt.subplots(1,2,figsize=(12,5.2));ax=axes[0]
ax.scatter(L.normalized_edit_distance,L.aligned_mismatch,s=15,alpha=.18,color='#24669A',edgecolors='none')
ax.axvline(.3,color='#B65A22',linestyle='--',lw=1.4);ax.axhline(.8,color='#B65A22',linestyle='--',lw=1.4)
ax.set(xlim=(-.03,1.03),ylim=(-.03,1.03),xlabel='Distancia de edición normalizada',ylabel='Discrepancia por posición')
ax.set_title('Desfase: diagnóstico de 1.649 ventanas',loc='left',pad=14)
ax.text(.36,.06,'309 ventanas cumplen:\ndiscrepancia ≥ 0,8 y edición ≤ 0,3',fontsize=10,bbox=dict(facecolor='white',alpha=.9,edgecolor='none'))
ax=axes[1];rows=D['summary'];pos=np.arange(4)
full=np.array([r['full_generation_s']/60 for r in rows]);look=np.array([r['lookahead_s']/60 for r in rows])
ax.bar(pos,full,color='#24669A',label='Ramas completas');ax.bar(pos,look,bottom=full,color='#B65A22',label='Lookaheads')
for i,v in enumerate(full+look):ax.text(i,v+.6,f'{v:.1f}',ha='center')
ax.set_xticks(pos,[r['selector'] for r in rows]);ax.set_ylim(0,40);ax.set_ylabel('Minutos de generación registrados');ax.set_title('Costos reconstruidos por selector',loc='left',pad=14);ax.legend(fontsize=9)
fig.text(.04,-.055,'El diagnóstico no establece equivalencia semántica. Costos: sumas de latencias de generación, sin baseline ni tests.\nLos selectores comparten ramas; las barras no se suman. No representan mediciones end-to-end independientes.',fontsize=9,color='#444444')
fig.tight_layout(w_pad=2);save(fig,'02_desfase_costos')
fig,axes=plt.subplots(1,2,figsize=(12,5.3),sharey=True)
fs=['mean_entropy','max_entropy','mean_margin','min_margin'];labels=['Mayor entropía media','Mayor entropía máxima','Menor margen medio','Menor margen mínimo']
for ax,ds in zip(axes,['HumanEval','MBPP']):
    for i,f in enumerate(fs):
        r=next(x for x in PR['associations'] if x['dataset']==ds and x['feature']==f);v=r['auc_high_predicts_failure'];lo,hi=r['auc_bootstrap95']
        if 'margin' in f:v,lo,hi=1-v,1-hi,1-lo
        ax.errorbar(v,3-i,xerr=[[v-lo],[hi-v]],fmt='o',color='#24669A',capsize=5,markersize=7)
        ax.text(.98,3-i,f"q={r['q_bh_16']:.3f}",ha='right',va='center',fontsize=9)
    ax.axvline(.5,color='#666666',ls='--',lw=1);ax.set_xlim(.2,1);ax.set_yticks(range(4),labels[::-1]);ax.set_xlabel('AUC para distinguir fallos · IC bootstrap 95%');ax.set_title(ds,loc='left',pad=16);ax.grid(axis='x',alpha=.15)
fig.suptitle('Experimentos previos: incertidumbre y fallo del programa',x=.03,ha='left',fontsize=16,y=1.02)
fig.text(.03,-.065,'HumanEval: 25 fallos / 164 tareas. MBPP: 15 fallos / 100 tareas. Asociación retrospectiva, sin validación predictiva externa.\nq: ajuste Benjamini–Hochberg de 16 pruebas exploratorias; los IC de AUC son marginales, no ajustados.',fontsize=9,color='#444444')
fig.tight_layout(w_pad=2);save(fig,'03_asociaciones_previas')
print('Created 3 PNG and 3 SVG figures')
