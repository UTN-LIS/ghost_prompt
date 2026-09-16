import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
src = ROOT / 'aligned_validation' / 'aligned_positions.csv'
out_csv = ROOT / 'fourier_position_spectrum.csv'
out_json = ROOT / 'fourier_results.json'

df = pd.read_csv(src)
metrics = {
    'aligned_persistence': 'persistencia alineada',
    'aligned_weighted_divergence': 'divergencia semántica alineada',
    'aligned_semantic_score': 'score semántico alineado',
}

positions = np.arange(int(df.position.min()), int(df.position.max()) + 1)
rows = []
result = {'source': str(src), 'n_rows': int(len(df)), 'position_min': int(positions.min()), 'position_max': int(positions.max()), 'metrics': {}}

for col, label in metrics.items():
    g = df.groupby('position')[col].agg(['mean','std','count']).reindex(positions)
    # Linear interpolation is used only to obtain an evenly spaced signal for FFT;
    # the original missing positions and support counts remain in the output.
    y = g['mean'].interpolate(limit_direction='both').to_numpy(float)
    x = np.arange(len(y), dtype=float)
    coef = np.polyfit(x, y, 1)
    detr = y - np.polyval(coef, x)
    spec = np.abs(np.fft.rfft(detr)) ** 2
    freqs = np.fft.rfftfreq(len(detr), d=1.0)
    spec[0] = 0.0
    order = np.argsort(spec[1:])[::-1] + 1
    peaks = []
    for i in order[:8]:
        peaks.append({'bin': int(i), 'frequency_cycles_per_position': float(freqs[i]), 'period_positions': float(1/freqs[i]), 'power': float(spec[i]), 'relative_power': float(spec[i]/spec[1:].sum())})
    # lag autocorrelation of the detrended interpolated signal
    ac = np.correlate(detr, detr, mode='full')[len(detr)-1:]
    ac = ac / ac[0] if ac[0] else ac
    result['metrics'][col] = {'label': label, 'mean': float(np.nanmean(y)), 'std': float(np.nanstd(y)), 'linear_trend_per_position': float(coef[0]), 'top_peaks': peaks, 'autocorrelation_lags_1_to_10': [float(v) for v in ac[1:11]]}
    for p, m, s, n, yi in zip(positions, g['mean'], g['std'], g['count'], y):
        rows.append({'metric': col, 'position': int(p), 'mean_original': None if pd.isna(m) else float(m), 'std_original': None if pd.isna(s) else float(s), 'n_original': 0 if pd.isna(n) else int(n), 'mean_interpolated': float(yi)})

pd.DataFrame(rows).to_csv(out_csv, index=False)
out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False))
print(json.dumps(result, indent=2, ensure_ascii=False))
