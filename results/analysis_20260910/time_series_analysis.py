"""Temporal diagnostics for branching signals.

Generation position is an ordered decoding index, not physical time. This
script therefore reports descriptive trend/cycle diagnostics and uses
within-task randomisation as a robustness check, not as evidence of a
stationary stochastic process.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parent
LOOKAHEADS = ROOT / "../sheet_build_data/lookaheads.jsonl"
BRANCHES = ROOT / "../sheet_build_data/branches.jsonl"
OUTPUT = ROOT / "time_series_results.json"
SEED = 20260916
N_PERMUTATIONS = 2_000
N_BOOTSTRAP = 4_000

WINDOW_METRICS = {
    "persistence_after_forced": "persistencia",
    "weighted_semantic_divergence": "divergencia semántica ponderada",
    "anchor_score": "anchor score",
}
BRANCH_METRICS = {
    "entropy": "entropía",
    "probability_margin": "margen top-1/top-2",
    "semantic_lookahead_score": "score semántico original",
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def interpolated_position_means(position: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    sums = np.zeros(len(grid), dtype=float)
    counts = np.zeros(len(grid), dtype=int)
    np.add.at(sums, position - grid[0], values)
    np.add.at(counts, position - grid[0], 1)
    means = np.divide(sums, counts, out=np.full(len(grid), np.nan), where=counts > 0)
    observed = np.flatnonzero(counts)
    return np.interp(np.arange(len(grid)), observed, means[observed])


def spectrum(series: np.ndarray) -> dict:
    x = np.arange(len(series), dtype=float)
    slope, intercept = np.polyfit(x, series, 1)
    residual = series - (intercept + slope * x)
    power = np.abs(np.fft.rfft(residual)) ** 2
    frequency = np.fft.rfftfreq(len(residual), d=1.0)
    power[0] = 0.0
    total = power[1:].sum()
    order = np.argsort(power[1:])[::-1] + 1
    peaks = [
        {
            "bin": int(i),
            "frequency_cycles_per_position": float(frequency[i]),
            "period_positions": float(1 / frequency[i]),
            "relative_power": float(power[i] / total) if total else 0.0,
        }
        for i in order[:5]
    ]
    acf = []
    for lag in range(1, min(11, len(residual))):
        acf.append(float(np.corrcoef(residual[:-lag], residual[lag:])[0, 1]))
    return {
        "linear_slope_per_position": float(slope),
        "autocorrelation_lags_1_to_10": acf,
        "top_peaks": peaks,
        "max_relative_power": float(power[order[0]] / total) if len(order) and total else 0.0,
    }


def task_bootstrap_ci(rows: list[dict], metric: str, rng: np.random.Generator) -> list[float]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    tasks = list(grouped)
    draws = []
    for _ in range(N_BOOTSTRAP):
        sampled = [row for task in rng.choice(tasks, len(tasks), replace=True) for row in grouped[task]]
        passed = [float(row[metric]) for row in sampled if row["passed"]]
        failed = [float(row[metric]) for row in sampled if not row["passed"]]
        if passed and failed:
            draws.append(float(np.mean(passed) - np.mean(failed)))
    return [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]


def within_task_label_permutation_p(rows: list[dict], metric: str, observed: float, rng: np.random.Generator) -> float:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    extreme = 0
    for _ in range(N_PERMUTATIONS):
        values, labels = [], []
        for task_rows in grouped.values():
            values.extend(float(row[metric]) for row in task_rows)
            labels.extend(rng.permutation([bool(row["passed"]) for row in task_rows]))
        values, labels = np.asarray(values), np.asarray(labels)
        statistic = float(values[labels].mean() - values[~labels].mean())
        extreme += abs(statistic) >= abs(observed)
    return float((extreme + 1) / (N_PERMUTATIONS + 1))


def main() -> None:
    rng = np.random.default_rng(SEED)
    lookaheads = read_jsonl(LOOKAHEADS)
    branches = read_jsonl(BRANCHES)
    grid = np.arange(min(int(row["position"]) for row in lookaheads), max(int(row["position"]) for row in lookaheads) + 1)
    positions = np.asarray([int(row["position"]) for row in lookaheads])

    by_task: dict[str, list[dict]] = defaultdict(list)
    for row in lookaheads:
        by_task[row["task_id"]].append(row)

    temporal = {}
    for metric, label in WINDOW_METRICS.items():
        values = np.asarray([float(row[metric]) for row in lookaheads])
        observed_series = interpolated_position_means(positions, values, grid)
        observed = spectrum(observed_series)
        null_max_power = []
        for _ in range(N_PERMUTATIONS):
            shuffled_values = np.concatenate([
                rng.permutation([float(row[metric]) for row in rows]) for rows in by_task.values()
            ])
            shuffled_positions = np.concatenate([
                np.asarray([int(row["position"]) for row in rows]) for rows in by_task.values()
            ])
            null_max_power.append(spectrum(interpolated_position_means(shuffled_positions, shuffled_values, grid))["max_relative_power"])
        temporal[metric] = {
            "label": label,
            "rows": int(len(values)),
            "observed_positions": int(len(set(positions))),
            "missing_positions": int(len(grid) - len(set(positions))),
            "spectrum": observed,
            "within_task_permutation_p_for_largest_peak": float((sum(value >= observed["max_relative_power"] for value in null_max_power) + 1) / (N_PERMUTATIONS + 1)),
        }

    task_max_position = {task: max(int(row["position"]) for row in rows) for task, rows in by_task.items()}
    for row in branches:
        row["relative_position"] = int(row["position"]) / task_max_position[row["task_id"]]

    comparison = {}
    for metric, label in BRANCH_METRICS.items():
        passed = np.asarray([float(row[metric]) for row in branches if row["passed"]])
        failed = np.asarray([float(row[metric]) for row in branches if not row["passed"]])
        difference = float(passed.mean() - failed.mean())
        comparison[metric] = {
            "label": label,
            "pass_mean": float(passed.mean()),
            "fail_mean": float(failed.mean()),
            "pass_minus_fail": difference,
            "task_bootstrap_95_ci": task_bootstrap_ci(branches, metric, rng),
            "within_task_label_permutation_p": within_task_label_permutation_p(branches, metric, difference, rng),
        }

    phase_difference = float(
        np.mean([row["relative_position"] for row in branches if row["passed"]])
        - np.mean([row["relative_position"] for row in branches if not row["passed"]])
    )
    result = {
        "purpose": "Descriptive ordered-position analysis; generation position is not physical time.",
        "sources": {"lookaheads": str(LOOKAHEADS), "branches": str(BRANCHES)},
        "seed": SEED,
        "permutations": N_PERMUTATIONS,
        "bootstrap_resamples": N_BOOTSTRAP,
        "population": {
            "lookahead_windows": len(lookaheads),
            "unique_evaluated_branches": len(branches),
            "passing_branches": int(sum(bool(row["passed"]) for row in branches)),
            "failing_branches": int(sum(not bool(row["passed"]) for row in branches)),
            "tasks": len({row["task_id"] for row in branches}),
            "position_range": [int(grid.min()), int(grid.max())],
        },
        "all_window_temporal_structure": temporal,
        "pass_fail_comparison": comparison,
        "relative_phase_pass_fail": {
            "pass_mean": float(np.mean([row["relative_position"] for row in branches if row["passed"]])),
            "fail_mean": float(np.mean([row["relative_position"] for row in branches if not row["passed"]])),
            "pass_minus_fail": phase_difference,
            "task_bootstrap_95_ci": task_bootstrap_ci(branches, "relative_position", rng),
            "within_task_label_permutation_p": within_task_label_permutation_p(branches, "relative_position", phase_difference, rng),
        },
        "limitations": [
            "PASS/FAIL labels exist only for positions selected by one or more policies; this is not a random sample of all positions.",
            "Absolute position mixes tasks with different lengths and code structure; relative position is a secondary normalization.",
            "The FFT interpolates missing aggregate positions only to form an equally spaced diagnostic series.",
            "Permutation p-values are robustness checks conditional on this cohort and selection process, not confirmatory population inference.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
