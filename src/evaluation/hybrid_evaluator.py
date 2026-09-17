"""
Hybrid evaluator combining rule-based and LLM-as-judge evaluation.
"""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from .constraint_check import ConstraintChecker
from .llm_judge import LLMJudge


class HybridEvaluator:
    """
    Combines rule-based constraint checking with LLM-as-judge evaluation.
    Final score is a weighted blend of both components.
    """

    def __init__(
        self, judge_model, rule_weight: float = 0.5, judge_weight: float = 0.5
    ):
        """
        Args:
            judge_model: OpenAIModel instance used as judge
            rule_weight: Weight for rule-based score (default: 0.5)
            judge_weight: Weight for LLM-judge score (default: 0.5)
        """
        self.constraint_checker = ConstraintChecker()
        self.llm_judge = LLMJudge(judge_model)
        self.rule_weight = rule_weight
        self.judge_weight = judge_weight

        if abs(rule_weight + judge_weight - 1.0) > 0.01:
            raise ValueError(
                f"Weights must sum to 1.0, got {rule_weight + judge_weight}"
            )

    def evaluate_response(self, task, llm_response: str) -> Dict[str, Any]:
        """
        Evaluate response using hybrid approach.

        Rule score combines:
          - must_mention: deterministic keyword checks (ConstraintChecker)
          - must_not_recommend: semantic violation checks (LLMJudge)
        Judge score: qualitative relevance/coherence/faithfulness (LLMJudge)

        Args:
            task: ReasoningTask object
            llm_response: Model's response to evaluate

        Returns:
            Complete evaluation results
        """
        constraints = (
            getattr(task, "ground_truth_constraints", None)
            or task.get("ground_truth_constraints", [])
        )

        # 1. Deterministic must_mention checks
        rule_results = self.constraint_checker.evaluate_task(llm_response, task)

        # 2. LLM judge: must_not_recommend violation checks (batched, single call)
        must_not_constraints = [
            c for c in constraints if c.get("constraint_type") == "must_not_recommend"
        ]
        must_not_check = self.llm_judge.check_must_not_violations(llm_response, must_not_constraints)

        # 3. Merge must_not results into the rule score
        must_not_violations = 0
        must_not_details = []
        for item in must_not_check["results"]:
            passed = not item["violated"]
            if not passed:
                must_not_violations += 1
            must_not_details.append({
                "constraint_id": item["constraint_id"],
                "type": "must_not_recommend",
                "passed": passed,
                "details": item["reasoning"],
            })

        combined_passed = rule_results["passed_constraints"] + (len(must_not_constraints) - must_not_violations)
        combined_total = rule_results["total_constraints"] + len(must_not_constraints)
        rule_score = combined_passed / combined_total if combined_total > 0 else 1.0

        # 4. Qualitative judge scoring
        judge_results = self.llm_judge.evaluate_response(task, llm_response)

        hybrid_score = self.rule_weight * rule_score + self.judge_weight * judge_results["judge_score"]

        return {
            # Task identification
            "task_id": getattr(task, "task_id", None) or task.get("task_id", "unknown"),
            "reasoning_type": getattr(task, "reasoning_type", None) or task.get("reasoning_type", "unknown"),
            "game_phase": getattr(task, "game_phase", None) or task.get("game_phase", "unknown"),
            # Scores
            "rule_score": rule_score,
            "judge_score": judge_results["judge_score"],
            "hybrid_score": hybrid_score,
            # Judge breakdown
            "relevance": judge_results["relevance"],
            "relevance_justification": judge_results["relevance_justification"],
            "coherence": judge_results["coherence"],
            "coherence_justification": judge_results["coherence_justification"],
            "faithfulness": judge_results["faithfulness"],
            "faithfulness_justification": judge_results["faithfulness_justification"],
            "judge_success": judge_results["success"],
            "must_not_judge_success": must_not_check["success"],
            # Rule breakdown
            "constraints_passed": combined_passed,
            "constraints_total": combined_total,
            "must_mention_passed": rule_results["must_mention_passed"],
            "must_not_violations": must_not_violations,
            "must_not_total": len(must_not_constraints),
            "has_rule_violation": rule_score < 1.0,
            "has_critical_error": must_not_violations > 0,
            "rule_details": rule_results["detailed_results"] + must_not_details,
            # Original response
            "llm_response": llm_response,
        }

    def set_weights(self, rule_weight: float, judge_weight: float):
        """Update scoring weights."""
        if abs(rule_weight + judge_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0")
        self.rule_weight = rule_weight
        self.judge_weight = judge_weight

    def _judge_rule_agreement(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute agreement between rule-based and LLM-judge scores.

        Metrics:
        - pearson_r: correlation in how both components rank tasks (direction agreement)
        - mad: mean absolute difference between scores (magnitude agreement)

        Args:
            results: List of result dicts from evaluate_response()

        Returns:
            Dict with pearson_r and mad
        """
        pairs = [
            (r["rule_score"], r["judge_score"])
            for r in results
            if "rule_score" in r and "judge_score" in r
        ]

        if len(pairs) < 2:
            return {"pearson_r": None, "mad": None, "n": len(pairs)}

        rule_scores = [p[0] for p in pairs]
        judge_scores = [p[1] for p in pairs]
        n = len(pairs)

        # Mean absolute difference
        mad = sum(abs(r - j) for r, j in pairs) / n

        # Pearson correlation
        mean_r = sum(rule_scores) / n
        mean_j = sum(judge_scores) / n
        cov = sum((r - mean_r) * (j - mean_j) for r, j in pairs) / n
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in rule_scores) / n)
        std_j = math.sqrt(sum((j - mean_j) ** 2 for j in judge_scores) / n)

        if std_r == 0 or std_j == 0:
            pearson_r = None  # No variance — correlation undefined
        else:
            pearson_r = cov / (std_r * std_j)

        return {
            "pearson_r": round(pearson_r, 4) if pearson_r is not None else None,
            "mad": round(mad, 4),
            "n": n,
        }

    def aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute aggregate statistics across a list of evaluation results.

        Args:
            results: List of result dicts from evaluate_response()

        Returns:
            Dict with overall averages and per-reasoning-type breakdown
        """
        if not results:
            return {}

        def avg(values):
            return sum(values) / len(values) if values else 0.0

        score_keys = ["hybrid_score", "rule_score", "judge_score", "relevance", "coherence", "faithfulness"]

        n = len(results)

        # Overall averages
        overall = {k: avg([r[k] for r in results if k in r]) for k in score_keys}
        overall["n_tasks"] = n
        overall["constraints_passed"] = sum(r.get("constraints_passed", 0) for r in results)
        overall["constraints_total"] = sum(r.get("constraints_total", 0) for r in results)
        overall["must_not_violations"] = sum(r.get("must_not_violations", 0) for r in results)
        overall["rule_violation_rate"] = round(
            sum(1 for r in results if r.get("has_rule_violation", False)) / n, 4
        )
        overall["critical_error_rate"] = round(
            sum(1 for r in results if r.get("has_critical_error", False)) / n, 4
        )

        # Per reasoning type breakdown
        by_type: Dict[str, List] = {}
        for r in results:
            rt = r.get("reasoning_type", "unknown")
            by_type.setdefault(rt, []).append(r)

        by_reasoning_type = {
            rt: {
                "n_tasks": len(group),
                **{k: avg([r[k] for r in group if k in r]) for k in score_keys},
            }
            for rt, group in sorted(by_type.items())
        }

        # Per game phase breakdown (early → mid → late)
        phase_order = ["early", "mid", "late"]
        by_phase_raw: Dict[str, List] = {}
        for r in results:
            phase = r.get("game_phase") or "unknown"
            by_phase_raw.setdefault(phase, []).append(r)

        by_game_phase = {
            phase: {
                "n_tasks": len(by_phase_raw[phase]),
                **{k: avg([r[k] for r in by_phase_raw[phase] if k in r]) for k in score_keys},
            }
            for phase in phase_order
            if phase in by_phase_raw
        }
        # Append any unexpected phase values at the end
        for phase, group in sorted(by_phase_raw.items()):
            if phase not in by_game_phase:
                by_game_phase[phase] = {
                    "n_tasks": len(group),
                    **{k: avg([r[k] for r in group if k in r]) for k in score_keys},
                }

        return {
            "overall": overall,
            "by_reasoning_type": by_reasoning_type,
            "by_game_phase": by_game_phase,
            "judge_rule_agreement": self._judge_rule_agreement(results),
        }

    def save_results(
        self,
        results: List[Dict[str, Any]],
        output_path: Path,
        run_meta: Optional[Dict[str, Any]] = None,
    ):
        """
        Save evaluation results and run metadata to a JSON file.

        Args:
            results: List of result dicts from evaluate_response()
            output_path: Path to write the JSON file
            run_meta: Optional metadata about the run (model, dataset, timestamp, etc.)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "meta": {
                "saved_at": datetime.now().isoformat(),
                "n_tasks": len(results),
                **(run_meta or {}),
            },
            "summary": self.aggregate_results(results),
            "results": results,
        }

        with open(output_path, "w") as f:
            json.dump(payload, f, indent=2)

        print(f"Results saved to {output_path}")
