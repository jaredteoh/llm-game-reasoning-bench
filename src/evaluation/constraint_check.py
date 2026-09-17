from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ConstraintResult:
    constraint_id: str
    constraint_type: str
    passed: bool
    details: str


class ConstraintChecker:
    """
    Evaluates responses against deterministic constraints.
    Implements rule-based component of hybrid evaluation.
    """

    def check_must_mention(
        self, response: str, constraint: Dict[str, Any]
    ) -> ConstraintResult:
        """
        Check if response mentions required keywords.

        Args:
            response: LLM's response text
            constraint: Dict with 'keywords' and 'min_mentions' keys

        Returns:
            ConstraintResult indicating pass/fail
        """
        keywords = constraint["parameters"]["keywords"]
        min_mentions = constraint["parameters"].get("min_mentions", 1)

        response_lower = response.lower()
        matched_keywords = [kw for kw in keywords if kw.lower() in response_lower]
        distinct_matches = len(matched_keywords)

        passed = distinct_matches >= min_mentions

        return ConstraintResult(
            constraint_id=constraint["constraint_id"],
            constraint_type="must_mention",
            passed=passed,
            details=f"Matched {distinct_matches}/{len(keywords)} distinct keywords (required: {min_mentions}): {matched_keywords if matched_keywords else 'none'}",
        )

    def check_must_not_recommend(
        self, response: str, constraint: Dict[str, Any]
    ) -> ConstraintResult:
        """
        Check if response avoids forbidden recommendations.

        Args:
            response: LLM's response text
            constraint: Dict with 'forbidden_recommendations' key

        Returns:
            ConstraintResult indicating pass/fail
        """
        forbidden = constraint["parameters"]["forbidden_recommendations"]
        response_lower = response.lower()

        violations = []
        for forbidden_phrase in forbidden:
            if forbidden_phrase.lower() in response_lower:
                violations.append(forbidden_phrase)

        passed = len(violations) == 0

        return ConstraintResult(
            constraint_id=constraint["constraint_id"],
            constraint_type="must_not_recommend",
            passed=passed,
            details=f"Violations: {violations}" if violations else "No violations",
        )

    def evaluate_task(self, response: str, task: "ReasoningTask") -> Dict[str, Any]:
        """
        Evaluate response against all constraints for a task.

        Args:
            response: LLM's response text
            task: ReasoningTask object with constraints

        Returns:
            Dict with score and detailed results
        """
        results = []

        # Check must_mention constraints only.
        # must_not_recommend is handled separately by LLMJudge.check_must_not_violations
        # in HybridEvaluator and merged back before scoring.
        for constraint in task.ground_truth_constraints:
            if constraint["constraint_type"] == "must_mention":
                result = self.check_must_mention(response, constraint)
                results.append(result)

        # Calculate score
        total_constraints = len(results)
        passed_constraints = sum(1 for r in results if r.passed)
        score = passed_constraints / total_constraints if total_constraints > 0 else 1.0

        # Separate by type
        must_mention_results = [
            r for r in results if r.constraint_type == "must_mention"
        ]
        must_not_results = [
            r for r in results if r.constraint_type == "must_not_recommend"
        ]

        return {
            "score": score,
            "total_constraints": total_constraints,
            "passed_constraints": passed_constraints,
            "failed_constraints": total_constraints - passed_constraints,
            "must_mention_passed": sum(1 for r in must_mention_results if r.passed),
            "must_mention_total": len(must_mention_results),
            "must_not_violations": sum(1 for r in must_not_results if not r.passed),
            "must_not_total": len(must_not_results),
            "detailed_results": [
                {
                    "constraint_id": r.constraint_id,
                    "type": r.constraint_type,
                    "passed": r.passed,
                    "details": r.details,
                }
                for r in results
            ],
        }


# Example usage
if __name__ == "__main__":
    # Test with a sample task
    sample_response = """
    Blue should start Baron because they have vision control around the pit
    and a gold advantage of 2,278. With all members alive and vision secured,
    this is a safe opportunity to secure the objective.
    """

    sample_constraint_mention = {
        "constraint_id": "baron_vision",
        "constraint_type": "must_mention",
        "parameters": {"keywords": ["vision", "control", "ward"], "min_mentions": 1},
    }

    sample_constraint_not = {
        "constraint_id": "no_blind_baron",
        "constraint_type": "must_not_recommend",
        "parameters": {
            "forbidden_recommendations": ["blind baron", "baron without vision"]
        },
    }

    checker = ConstraintChecker()

    result1 = checker.check_must_mention(sample_response, sample_constraint_mention)
    print(f"Must mention result: {result1}")

    result2 = checker.check_must_not_recommend(sample_response, sample_constraint_not)
    print(f"Must not recommend result: {result2}")
