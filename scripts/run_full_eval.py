"""
Run hybrid evaluation across the FULL dataset (or a filtered subset) — not a
random sample. This is the unattended, long-running counterpart to
sample_tasks.py, built for runs over all ~300 tasks.

Differences from sample_tasks.py:
- Iterates every task (in dataset order, optionally filtered by --type) instead
  of randomly sampling --n of them.
- Catches per-task errors so a single transient failure (rate limit, flaky
  response, etc.) doesn't kill a multi-hour run — failed task_ids are logged
  and reported at the end.
- Periodically checkpoints partial results to --output, and can --resume a
  previously interrupted run by skipping task_ids already present in the file.
- Always runs full hybrid evaluation (rule-based + GPT judge) — there's no
  point doing a "full run" without scoring.

Usage:
    python scripts/run_full_eval.py --output results/gemini_full_run.json
    python scripts/run_full_eval.py --model models/gemini-2.5-flash --judge-model gpt-4o-mini --output results/gemini_full_run.json
    python scripts/run_full_eval.py --type causal_inference --output results/gemini_causal.json
    python scripts/run_full_eval.py --output results/gemini_full_run.json --resume       # continue an interrupted run
    python scripts/run_full_eval.py --output results/smoke_test.json --limit 5           # smoke test before the real run
"""

import sys
import json
import time
import argparse
import traceback
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from sample_tasks import MODEL_REGISTRY, load_tasks, run_task, print_separator
from models.ollama import OllamaModel
from models.openai import OpenAIModel
from evaluation.hybrid_evaluator import HybridEvaluator


def load_checkpoint(output_path: Path) -> List[Dict[str, Any]]:
    """Load previously-saved results from --output, if any (for --resume)."""
    if not output_path.exists():
        return []
    try:
        with open(output_path) as f:
            data = json.load(f)
        return data.get("results", [])
    except (json.JSONDecodeError, KeyError):
        return []


def main():
    project_root = Path(__file__).parent.parent
    default_dataset = project_root / "output" / "milestone3" / "dataset_v6.json"

    parser = argparse.ArgumentParser(
        description="Run hybrid evaluation over the full dataset (unattended, resumable)"
    )
    parser.add_argument("--dataset", type=Path, default=default_dataset)
    parser.add_argument(
        "--type",
        dest="reasoning_type",
        default=None,
        help="Filter by reasoning type (e.g. causal_inference, strategic_planning, error_diagnosis, resource_logic, spatial_reasoning)",
    )
    parser.add_argument(
        "--model",
        default="models/gemini-2.5-flash",
        help=f"Inference model. Registered: {', '.join(MODEL_REGISTRY)}",
    )
    parser.add_argument(
        "--judge-model",
        default="gpt-4o-mini",
        help="Judge model (must be an OpenAI model, default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output / checkpoint JSON file, e.g. results/gemini_full_run.json",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=10,
        help="Checkpoint to --output every N completed tasks (default: 10)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip task_ids already present in --output and continue from there",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of tasks run — useful for a smoke test before the real run",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Dataset not found: {args.dataset}")
        sys.exit(1)

    tasks = load_tasks(str(args.dataset), args.reasoning_type)
    if not tasks:
        filter_msg = (
            f" with type '{args.reasoning_type}'" if args.reasoning_type else ""
        )
        print(f"No tasks found{filter_msg} in {args.dataset}")
        sys.exit(1)

    if args.limit is not None:
        tasks = tasks[: args.limit]

    print(f"Dataset: {args.dataset.name}  ({len(tasks)} task(s) targeted)")
    print(f"Model:   {args.model}")
    print(f"Judge:   {args.judge_model}")
    print(f"Output:  {args.output}")
    if args.reasoning_type:
        print(f"Filter:  {args.reasoning_type}")

    # ---- Resume support: skip task_ids already completed in a prior run ----
    done_results: List[Dict[str, Any]] = []
    done_ids = set()
    if args.resume:
        done_results = load_checkpoint(args.output)
        done_ids = {r["task_id"] for r in done_results}
        if done_results:
            print(
                f"Resuming: {len(done_results)} task(s) already completed in {args.output.name}, skipping them."
            )

    pending = [t for t in tasks if t.task_id not in done_ids]
    if not pending:
        print("Nothing to do — all targeted tasks are already completed.")
        return

    # ---- Set up inference model ----
    model_class = MODEL_REGISTRY.get(args.model)
    if model_class is None:
        print(f"Unknown model '{args.model}'. Registered models:")
        for name in MODEL_REGISTRY:
            print(f"  {name}")
        sys.exit(1)

    model = model_class(model_name=args.model, temperature=0.0)
    print(f"\nChecking {model_class.__name__} connection...", flush=True)
    if not model.test_connection():
        if model_class is OllamaModel:
            print("Failed. Make sure Ollama is running: ollama serve")
        else:
            print("Failed. Check your API key in .env")
        sys.exit(1)
    print("Connected.")

    # ---- Set up evaluator (always on for a full run) ----
    judge_model_class = MODEL_REGISTRY.get(args.judge_model)
    if judge_model_class is None or judge_model_class is not OpenAIModel:
        print(f"Judge model must be an OpenAI model. Got: {args.judge_model}")
        sys.exit(1)
    judge_model = OpenAIModel(model_name=args.judge_model, temperature=0.0)
    print("Checking OpenAIModel connection...", flush=True)
    if not judge_model.test_connection():
        print("Failed. Check your OPENAI_API_KEY in .env")
        sys.exit(1)
    print("Connected.")
    evaluator = HybridEvaluator(judge_model)

    run_meta = {
        "dataset": args.dataset.name,
        "model": args.model,
        "judge_model": args.judge_model,
        "reasoning_type_filter": args.reasoning_type,
        "full_run": True,
    }

    # ---- Run ----
    all_results: List[Dict[str, Any]] = list(done_results)
    failed: List[str] = []
    start = time.time()
    total = len(tasks)

    print()
    for i, task in enumerate(pending, 1):
        elapsed = time.time() - start
        print(
            f"\n[{len(done_results) + i}/{total}]  (this session: {i}/{len(pending)}, elapsed: {elapsed:.0f}s)"
        )
        try:
            result = run_task(task, model, run_eval=True, evaluator=evaluator)
            if result is not None:
                all_results.append(result)
        except Exception as e:
            print(f"  ERROR on task {task.task_id}: {e}")
            traceback.print_exc()
            failed.append(task.task_id)
            continue

        if args.save_every and (i % args.save_every == 0):
            evaluator.save_results(
                all_results,
                args.output,
                {**run_meta, "failed_task_ids": failed, "status": "in_progress"},
            )
            print(f"  [checkpoint saved: {len(all_results)} result(s)]")

    elapsed_total = time.time() - start
    print_separator()
    print(
        f"Done. Completed {len(all_results)}/{total} task(s) in {elapsed_total:.0f}s."
    )
    if failed:
        print(f"Failed task(s) ({len(failed)}): {failed}")

    run_meta["failed_task_ids"] = failed
    run_meta["status"] = "complete" if not failed else "complete_with_failures"

    if all_results:
        evaluator.save_results(all_results, args.output, run_meta)

        summary = evaluator.aggregate_results(all_results)
        overall = summary["overall"]
        print(f"\n{'FINAL SUMMARY':^70}")
        print_separator("-")
        print(f"  Hybrid Score:     {overall['hybrid_score']:.0%}  (avg)")
        print(f"  Rule Score:       {overall['rule_score']:.0%}  (avg)")
        print(f"  Judge Score:      {overall['judge_score']:.0%}  (avg)")
        print(f"    Relevance:      {overall['relevance']:.0%}")
        print(f"    Coherence:      {overall['coherence']:.0%}")
        print(f"    Faithfulness:   {overall['faithfulness']:.0%}")
        print(
            f"  Constraints:      {overall['constraints_passed']}/{overall['constraints_total']} passed"
        )
        print(f"  Rule Violation Rate:   {overall['rule_violation_rate']:.0%}")
        print(f"  Critical Error Rate:   {overall['critical_error_rate']:.0%}")

        if len(summary["by_reasoning_type"]) > 1:
            print(f"\n  By reasoning type:")
            for rt, stats in summary["by_reasoning_type"].items():
                print(
                    f"    {rt:<28} {stats['hybrid_score']:.0%}  ({stats['n_tasks']} task{'s' if stats['n_tasks'] > 1 else ''})"
                )

        if len(summary["by_game_phase"]) > 1:
            print(f"\n  By game phase:")
            for phase, stats in summary["by_game_phase"].items():
                print(
                    f"    {phase:<28} {stats['hybrid_score']:.0%}  ({stats['n_tasks']} task{'s' if stats['n_tasks'] > 1 else ''})"
                )

        agreement = summary.get("judge_rule_agreement", {})
        if agreement.get("n", 0) >= 2:
            r = agreement["pearson_r"]
            mad = agreement["mad"]
            r_str = f"{r:+.3f}" if r is not None else "N/A"
            print(f"\n  Judge-Rule Agreement ({agreement['n']} tasks):")
            print(f"    Pearson r:  {r_str}")
            print(f"    MAD:        {mad:.3f}")
        print_separator()
        print(f"\nResults saved to {args.output}")
    else:
        print("No results collected — nothing saved.")


if __name__ == "__main__":
    main()
