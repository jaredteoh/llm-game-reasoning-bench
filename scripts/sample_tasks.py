"""
Sample real tasks from the dataset and test LLM responses.

Without --judge, the script only generates and prints responses.
With --judge, runs full hybrid evaluation: rule-based constraint checking + LLM-as-judge (GPT).

Usage:
    python scripts/sample_tasks.py                                           # 3 random tasks, gemini-2.5-flash, no eval
    python scripts/sample_tasks.py --n 5                                     # 5 random tasks
    python scripts/sample_tasks.py --type causal_inference                   # filter by type
    python scripts/sample_tasks.py --model gemini-2.0-flash                  # use a different inference model
    python scripts/sample_tasks.py --model llama3:latest                     # use Ollama
    python scripts/sample_tasks.py --dataset output/milestone3/dataset_v5.json
    python scripts/sample_tasks.py --no-eval                                 # skip all evaluation
    python scripts/sample_tasks.py --judge                                   # enable hybrid evaluation (uses GPT-4o-mini as judge)
    python scripts/sample_tasks.py --judge --judge-model gpt-4o              # use a different judge model
    python scripts/sample_tasks.py --judge --output results/run_001.json     # save results to file
"""

import sys
import json
import random
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.ollama import OllamaModel
from models.gemini import GeminiModel
from models.openai import OpenAIModel
from models.claude import ClaudeModel
from models.huggingface import HuggingFaceModel
from evaluation.hybrid_evaluator import HybridEvaluator

# Registry: add new models here
MODEL_REGISTRY = {
    # Ollama (local)
    "llama3:latest":                    OllamaModel,
    "llama3.1:8b":                      OllamaModel,
    # Gemini 2.5 series
    "models/gemini-2.5-pro":            GeminiModel,
    "models/gemini-2.5-flash":          GeminiModel,
    "gemini-2.5-flash":                 GeminiModel,
    "gemini-2.5-flash-lite":            GeminiModel,
    "models/gemini-2.5-flash-lite":     GeminiModel,
    # Gemini 2.5 thinking variants (thinkingBudget=8192)
    "gemini-2.5-flash-thinking":        GeminiModel,
    "gemini-2.5-flash-lite-thinking":   GeminiModel,
    "gemini-2.5-pro-thinking":          GeminiModel,
    # Gemini 3.x series
    "gemini-3.5-flash":                 GeminiModel,
    "gemini-3-flash-preview":           GeminiModel,
    "gemini-3.1-flash-lite":            GeminiModel,
    "gemini-3.1-pro-preview":           GeminiModel,
    # Gemini 3.x thinking variants (thinkingLevel="medium")
    "gemini-3.5-flash-thinking":        GeminiModel,
    "gemini-3.1-flash-lite-thinking":   GeminiModel,
    "gemini-3.1-pro-thinking":          GeminiModel,
    # OpenAI
    "gpt-4o-mini":                      OpenAIModel,
    "gpt-4o":                           OpenAIModel,
    "o4-mini":                          OpenAIModel,
    # Claude
    "claude-haiku-4-5-20251001":        ClaudeModel,
    "claude-sonnet-4-6":                ClaudeModel,
    "claude-opus-4-8":                  ClaudeModel,
    # Claude thinking variants (extended thinking, budget_tokens=4096)
    "claude-haiku-4-5-20251001-thinking": ClaudeModel,
    "claude-sonnet-4-6-thinking":        ClaudeModel,
    "claude-opus-4-8-thinking":          ClaudeModel,
    # HuggingFace Inference Providers
    "deepseek-ai/DeepSeek-V3":           HuggingFaceModel,
    "deepseek-ai/DeepSeek-R1":           HuggingFaceModel,
    "deepseek-ai/DeepSeek-R1-0528":      HuggingFaceModel,
    # DeepSeek-R1 thinking variants (strips <think> trace)
    "deepseek-ai/DeepSeek-R1-thinking":       HuggingFaceModel,
    "deepseek-ai/DeepSeek-R1-0528-thinking":  HuggingFaceModel,
}


@dataclass
class TaskProxy:
    """Minimal task wrapper compatible with all model generate_response interfaces."""
    task_id: str
    reasoning_type: str
    compressed_match_state: str
    prompt: str
    ground_truth_constraints: list
    expected_reasoning_elements: list
    timestamp_min: Optional[float]
    game_phase: Optional[str]


def load_tasks(dataset_path: str, reasoning_type: Optional[str] = None) -> List[TaskProxy]:
    with open(dataset_path) as f:
        data = json.load(f)

    tasks = []
    for t in data["tasks"]:
        if reasoning_type and t.get("reasoning_type") != reasoning_type:
            continue
        tasks.append(TaskProxy(
            task_id=t["task_id"],
            reasoning_type=t.get("reasoning_type", "unknown"),
            compressed_match_state=t["compressed_match_state"],
            prompt=t["prompt"],
            ground_truth_constraints=t.get("ground_truth_constraints", []),
            expected_reasoning_elements=t.get("expected_reasoning_elements", []),
            timestamp_min=t.get("timestamp_min"),
            game_phase=t.get("game_phase"),
        ))
    return tasks


def print_separator(char="=", width=70):
    print(char * width)


def run_task(task: TaskProxy, model, run_eval: bool,
             evaluator: Optional[HybridEvaluator] = None) -> Optional[Dict[str, Any]]:
    """
    Run a single task: generate response and optionally evaluate.

    Returns a result dict if evaluation was run, else None.
    """
    print_separator()
    print(f"Task:  {task.task_id}")
    ts = f"{task.timestamp_min}m" if task.timestamp_min is not None else "None"
    print(f"Type:  {task.reasoning_type}  |  Phase: {task.game_phase}  |  Timestamp: {ts}")
    print_separator("-")

    print("\n--- MATCH STATE ---")
    print(task.compressed_match_state)

    print("--- QUESTION ---")
    print(task.prompt)
    print()

    print("Generating response...", flush=True)
    response = model.generate_response(task)

    print("\n--- RESPONSE ---")
    print(response)
    print()

    if not run_eval or not evaluator:
        return None

    if not task.ground_truth_constraints:
        print("(No constraints defined for this task)\n")
        return None

    print("Evaluating...", flush=True)
    results = evaluator.evaluate_response(task, response)

    print("\n--- HYBRID EVALUATION ---")
    print(f"Hybrid Score:  {results['hybrid_score']:.0%}")
    print(f"  Rule Score:  {results['rule_score']:.0%}  ({results['constraints_passed']}/{results['constraints_total']} constraints passed)")
    print(f"  Judge Score: {results['judge_score']:.0%}")
    print()

    print("Constraints:")
    for detail in results["rule_details"]:
        status = "PASS" if detail["passed"] else "FAIL"
        print(f"  [{status}] {detail['constraint_id']}: {detail['details']}")
    print()

    if results["judge_success"]:
        print("Judge Scores:")
        print(f"  Relevance:    {results['relevance']:.0%}  — {results['relevance_justification']}")
        print(f"  Coherence:    {results['coherence']:.0%}  — {results['coherence_justification']}")
        print(f"  Faithfulness: {results['faithfulness']:.0%}  — {results['faithfulness_justification']}")
    else:
        print("Judge evaluation failed.")
    print()

    return {
        "task_id": task.task_id,
        "reasoning_type": task.reasoning_type,
        "game_phase": task.game_phase,
        "timestamp_min": task.timestamp_min,
        "prompt": task.prompt,
        "response": response,
        **results,
    }


def main():
    project_root = Path(__file__).parent.parent
    default_dataset = project_root / "output" / "milestone3" / "dataset_v5.json"

    parser = argparse.ArgumentParser(description="Sample tasks and evaluate LLM responses")
    parser.add_argument("--dataset", type=Path, default=default_dataset)
    parser.add_argument("--n", type=int, default=3, help="Number of tasks to sample")
    parser.add_argument("--type", dest="reasoning_type", default=None,
                        help="Filter by reasoning type (e.g. causal_inference, strategic_planning, error_diagnosis, resource_logic, spatial_reasoning)")
    parser.add_argument("--model", default="models/gemini-2.5-flash",
                        help=f"Inference model. Registered: {', '.join(MODEL_REGISTRY)}")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--no-eval", action="store_true", help="Skip all evaluation")
    parser.add_argument("--judge", action="store_true", help="Enable LLM-as-judge evaluation (uses OpenAI, costs tokens)")
    parser.add_argument("--judge-model", default="gpt-4o-mini", help="Judge model (default: gpt-4o-mini)")
    parser.add_argument("--output", type=Path, default=None, help="Save results to a JSON file (e.g. results/run_001.json)")
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Dataset not found: {args.dataset}")
        sys.exit(1)

    tasks = load_tasks(str(args.dataset), args.reasoning_type)
    if not tasks:
        filter_msg = f" with type '{args.reasoning_type}'" if args.reasoning_type else ""
        print(f"No tasks found{filter_msg} in {args.dataset}")
        sys.exit(1)

    if args.seed is not None:
        random.seed(args.seed)

    sample = random.sample(tasks, min(args.n, len(tasks)))

    print(f"Dataset: {args.dataset.name}  ({len(tasks)} tasks total)")
    print(f"Sampling {len(sample)} task(s)  |  Model: {args.model}")
    if args.reasoning_type:
        print(f"Filter: {args.reasoning_type}")
    if args.judge:
        print(f"Judge:  {args.judge_model} (hybrid evaluation enabled)")
    if args.output:
        print(f"Output: {args.output}")

    # Set up inference model
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

    # Set up evaluator
    evaluator = None

    if args.judge and not args.no_eval:
        judge_model_class = MODEL_REGISTRY.get(args.judge_model)
        if judge_model_class is None or judge_model_class is not OpenAIModel:
            print(f"Judge model must be an OpenAI model. Got: {args.judge_model}")
            sys.exit(1)
        judge_model = OpenAIModel(model_name=args.judge_model, temperature=0.0)
        print(f"Checking OpenAIModel connection...", flush=True)
        if not judge_model.test_connection():
            print("Failed. Check your OPENAI_API_KEY in .env")
            sys.exit(1)
        print("Connected.")
        evaluator = HybridEvaluator(judge_model)

    print()
    all_results = []
    for i, task in enumerate(sample, 1):
        print(f"\n[{i}/{len(sample)}]")
        result = run_task(task, model, run_eval=not args.no_eval, evaluator=evaluator)
        if result is not None:
            all_results.append(result)

    print_separator()
    print(f"Done. Ran {len(sample)} task(s).")

    if all_results and evaluator:
        summary = evaluator.aggregate_results(all_results)
        overall = summary["overall"]
        print(f"\n{'SUMMARY':^70}")
        print_separator("-")
        print(f"  Hybrid Score:     {overall['hybrid_score']:.0%}  (avg)")
        print(f"  Rule Score:       {overall['rule_score']:.0%}  (avg)")
        print(f"  Judge Score:      {overall['judge_score']:.0%}  (avg)")
        print(f"    Relevance:      {overall['relevance']:.0%}")
        print(f"    Coherence:      {overall['coherence']:.0%}")
        print(f"    Faithfulness:   {overall['faithfulness']:.0%}")
        print(f"  Constraints:      {overall['constraints_passed']}/{overall['constraints_total']} passed")
        print(f"  Rule Violation Rate:   {overall['rule_violation_rate']:.0%}  (tasks failing any constraint)")
        print(f"  Critical Error Rate:   {overall['critical_error_rate']:.0%}  (tasks with must_not_recommend violations)")
        if len(summary["by_reasoning_type"]) > 1:
            print(f"\n  By reasoning type:")
            for rt, stats in summary["by_reasoning_type"].items():
                print(f"    {rt:<28} {stats['hybrid_score']:.0%}  ({stats['n_tasks']} task{'s' if stats['n_tasks'] > 1 else ''})")
        if len(summary["by_game_phase"]) > 1:
            print(f"\n  By game phase:")
            for phase, stats in summary["by_game_phase"].items():
                print(f"    {phase:<28} {stats['hybrid_score']:.0%}  ({stats['n_tasks']} task{'s' if stats['n_tasks'] > 1 else ''})")

        agreement = summary.get("judge_rule_agreement", {})
        if agreement.get("n", 0) >= 2:
            r = agreement["pearson_r"]
            mad = agreement["mad"]
            r_str = f"{r:+.3f}" if r is not None else "N/A"
            print(f"\n  Judge-Rule Agreement ({agreement['n']} tasks):")
            print(f"    Pearson r:  {r_str}")
            print(f"    MAD:        {mad:.3f}")
        print_separator()

    if args.output and all_results and evaluator:
        run_meta = {
            "dataset": args.dataset.name,
            "model": args.model,
            "judge_model": args.judge_model,
            "reasoning_type_filter": args.reasoning_type,
            "seed": args.seed,
        }
        evaluator.save_results(all_results, args.output, run_meta)


if __name__ == "__main__":
    main()
