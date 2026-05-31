"""
Sample real tasks from the dataset and test LLM responses.

Usage:
    python scripts/sample_tasks.py                                          # 3 random tasks, llama3:latest
    python scripts/sample_tasks.py --n 5                                    # 5 random tasks
    python scripts/sample_tasks.py --type causal_inference                  # filter by type
    python scripts/sample_tasks.py --model gemini-2.5-flash-preview-05-20  # use Gemini
    python scripts/sample_tasks.py --model llama3:latest                    # use Ollama
    python scripts/sample_tasks.py --dataset output/milestone3/dataset_v3.json
    python scripts/sample_tasks.py --no-eval                                # skip constraint check
"""

import sys
import json
import random
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.ollama import OllamaModel
from models.gemini import GeminiModel
from evaluation.constraint_check import ConstraintChecker

# Registry: add new models here
MODEL_REGISTRY = {
    "llama3:latest":            OllamaModel,
    "llama3.1:8b":              OllamaModel,
    "models/gemini-2.5-flash":  GeminiModel,
    "gemini-2.0-flash":         GeminiModel,
    "gemini-2.0-flash-lite":    GeminiModel,
    "gemini-1.5-flash":         GeminiModel,
    "gemini-1.5-pro":           GeminiModel,
}


@dataclass
class TaskProxy:
    """Minimal task wrapper compatible with OllamaModel.generate_response."""
    task_id: str
    reasoning_type: str
    compressed_match_state: str
    prompt: str
    ground_truth_constraints: list
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
            timestamp_min=t.get("timestamp_min"),
            game_phase=t.get("game_phase"),
        ))
    return tasks


def print_separator(char="=", width=70):
    print(char * width)


def run_task(task: TaskProxy, model, checker: ConstraintChecker, run_eval: bool):
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

    if run_eval and task.ground_truth_constraints:
        print("--- CONSTRAINT CHECK ---")
        results = checker.evaluate_task(response, task)
        print(f"Score: {results['score']:.0%}  ({results['passed_constraints']}/{results['total_constraints']} passed)")

        for detail in results["detailed_results"]:
            status = "PASS" if detail["passed"] else "FAIL"
            print(f"  [{status}] {detail['constraint_id']}: {detail['details']}")
        print()
    elif not task.ground_truth_constraints:
        print("(No constraints defined for this task)\n")


def main():
    project_root = Path(__file__).parent.parent
    default_dataset = project_root / "output" / "milestone3" / "dataset_v3.json"

    parser = argparse.ArgumentParser(description="Sample real tasks and test Ollama responses")
    parser.add_argument("--dataset", type=Path, default=default_dataset)
    parser.add_argument("--n", type=int, default=3, help="Number of tasks to sample")
    parser.add_argument("--type", dest="reasoning_type", default=None,
                        help="Filter by reasoning type (e.g. causal_inference, strategic_planning, error_diagnosis, resource_logic, spatial_reasoning)")
    parser.add_argument("--model", default="models/gemini-2.5-flash",
                        help=f"Model to use. Registered: {', '.join(MODEL_REGISTRY)}")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--no-eval", action="store_true", help="Skip constraint evaluation")
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

    model_class = MODEL_REGISTRY.get(args.model)
    if model_class is None:
        print(f"Unknown model '{args.model}'. Registered models:")
        for name in MODEL_REGISTRY:
            print(f"  {name}")
        sys.exit(1)

    model = model_class(model_name=args.model, temperature=0.0)
    checker = ConstraintChecker()

    print(f"\nChecking {model_class.__name__} connection...", flush=True)
    if not model.test_connection():
        if model_class is OllamaModel:
            print("Failed. Make sure Ollama is running: ollama serve")
        else:
            print("Failed. Check your API key in .env")
        sys.exit(1)
    print("Connected.\n")

    for i, task in enumerate(sample, 1):
        print(f"\n[{i}/{len(sample)}]")
        run_task(task, model, checker, run_eval=not args.no_eval)

    print_separator()
    print(f"Done. Ran {len(sample)} task(s).")


if __name__ == "__main__":
    main()
