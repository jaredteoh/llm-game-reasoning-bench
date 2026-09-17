"""
Intra-run stability analysis across multiple evaluation runs.

Loads multiple JSON result files (produced by sample_tasks.py --judge --output)
and computes score variance per task to assess evaluation reliability.

Key insight:
- rule_score variance should be ~0 (deterministic) — any variance signals a bug
- judge_score variance measures LLM judge stability across runs

Usage:
    python scripts/stability_analysis.py results/run_1.json results/run_2.json results/run_3.json
    python scripts/stability_analysis.py results/run_*.json --top 5
    python scripts/stability_analysis.py results/run_*.json --output results/stability_report.json
"""

import sys
import json
import math
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional


SCORE_KEYS = ["hybrid_score", "rule_score", "judge_score", "relevance", "coherence", "faithfulness"]


def load_results(path: Path) -> List[Dict[str, Any]]:
    with open(path) as f:
        data = json.load(f)
    return data.get("results", [])


def variance(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def std_dev(values: List[float]) -> float:
    return math.sqrt(variance(values))


def compute_task_stability(runs: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    For each task present in all runs, compute per-score variance and std dev.

    Args:
        runs: List of result lists, one per run file

    Returns:
        List of per-task stability dicts, sorted by hybrid_score std dev descending
    """
    # Index each run by task_id
    indexed = [{r["task_id"]: r for r in run} for run in runs]

    # Only analyse tasks present in all runs
    common_ids = set(indexed[0].keys())
    for idx in indexed[1:]:
        common_ids &= set(idx.keys())

    task_stability = []
    for task_id in sorted(common_ids):
        task_runs = [idx[task_id] for idx in indexed]

        stability = {
            "task_id": task_id,
            "reasoning_type": task_runs[0].get("reasoning_type", "unknown"),
            "game_phase": task_runs[0].get("game_phase", "unknown"),
            "n_runs": len(task_runs),
        }

        for key in SCORE_KEYS:
            values = [r[key] for r in task_runs if key in r]
            if values:
                stability[f"{key}_mean"] = round(sum(values) / len(values), 4)
                stability[f"{key}_std"] = round(std_dev(values), 4)
                stability[f"{key}_min"] = round(min(values), 4)
                stability[f"{key}_max"] = round(max(values), 4)

        task_stability.append(stability)

    # Sort by hybrid_score std descending (most unstable first)
    task_stability.sort(key=lambda x: x.get("hybrid_score_std", 0.0), reverse=True)
    return task_stability


def compute_aggregate_stability(task_stability: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute overall stability metrics across all tasks."""
    if not task_stability:
        return {}

    def avg(values):
        return sum(values) / len(values) if values else 0.0

    aggregate = {"n_tasks": len(task_stability)}

    for key in SCORE_KEYS:
        std_values = [t[f"{key}_std"] for t in task_stability if f"{key}_std" in t]
        if std_values:
            aggregate[f"{key}_mean_std"] = round(avg(std_values), 4)
            aggregate[f"{key}_max_std"] = round(max(std_values), 4)

    return aggregate


def print_separator(char="=", width=70):
    print(char * width)


def print_report(
    run_files: List[Path],
    task_stability: List[Dict[str, Any]],
    aggregate: Dict[str, Any],
    top_n: int,
):
    print_separator()
    print(f"STABILITY ANALYSIS  ({len(run_files)} runs, {aggregate['n_tasks']} tasks)")
    print_separator("-")
    print(f"  Run files:")
    for f in run_files:
        print(f"    {f.name}")

    print(f"\n  Mean Std Dev across tasks:")
    print(f"    {'hybrid_score':<20} {aggregate.get('hybrid_score_mean_std', 0):.4f}")
    print(f"    {'rule_score':<20} {aggregate.get('rule_score_mean_std', 0):.4f}  (expected ~0.0000 — deterministic)")
    print(f"    {'judge_score':<20} {aggregate.get('judge_score_mean_std', 0):.4f}")
    print(f"    {'relevance':<20} {aggregate.get('relevance_mean_std', 0):.4f}")
    print(f"    {'coherence':<20} {aggregate.get('coherence_mean_std', 0):.4f}")
    print(f"    {'faithfulness':<20} {aggregate.get('faithfulness_mean_std', 0):.4f}")

    # Flag rule_score instability
    rule_std = aggregate.get("rule_score_mean_std", 0.0)
    if rule_std > 0.001:
        print(f"\n  WARNING: rule_score std={rule_std:.4f} > 0 — deterministic check is unstable, investigate constraint logic")

    print(f"\n  Top {top_n} most unstable tasks (by hybrid_score std):")
    print_separator("-")
    for t in task_stability[:top_n]:
        print(f"  {t['task_id']}")
        print(f"    Type: {t['reasoning_type']}  |  Phase: {t['game_phase']}")
        print(f"    hybrid  mean={t.get('hybrid_score_mean', 0):.3f}  std={t.get('hybrid_score_std', 0):.4f}  range=[{t.get('hybrid_score_min', 0):.3f}, {t.get('hybrid_score_max', 0):.3f}]")
        print(f"    rule    mean={t.get('rule_score_mean', 0):.3f}  std={t.get('rule_score_std', 0):.4f}")
        print(f"    judge   mean={t.get('judge_score_mean', 0):.3f}  std={t.get('judge_score_std', 0):.4f}")
        print()

    print_separator()


def main():
    parser = argparse.ArgumentParser(description="Intra-run stability analysis across multiple evaluation runs")
    parser.add_argument("run_files", nargs="+", type=Path, help="JSON result files from sample_tasks.py --output")
    parser.add_argument("--top", type=int, default=5, help="Number of most unstable tasks to show (default: 5)")
    parser.add_argument("--output", type=Path, default=None, help="Save stability report to JSON file")
    args = parser.parse_args()

    if len(args.run_files) < 2:
        print("Error: at least 2 run files are required for stability analysis")
        sys.exit(1)

    for f in args.run_files:
        if not f.exists():
            print(f"Error: file not found: {f}")
            sys.exit(1)

    runs = [load_results(f) for f in args.run_files]

    # Validate all runs have results
    for f, run in zip(args.run_files, runs):
        if not run:
            print(f"Warning: no results found in {f.name} — was it run with --judge?")

    task_stability = compute_task_stability(runs)
    if not task_stability:
        print("No tasks found in common across all run files.")
        sys.exit(1)

    aggregate = compute_aggregate_stability(task_stability)

    print_report(args.run_files, task_stability, aggregate, top_n=args.top)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "run_files": [str(f) for f in args.run_files],
            "aggregate": aggregate,
            "task_stability": task_stability,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Stability report saved to {args.output}")


if __name__ == "__main__":
    main()
