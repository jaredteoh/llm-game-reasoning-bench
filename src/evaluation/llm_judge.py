"""
LLM-as-Judge evaluation component.
Uses GPT as judge, scoring responses on three independent dimensions:
Relevance, Coherence, and Faithfulness — each in a separate focused call.
Structured outputs (Pydantic) are used to guarantee consistent score format.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from .prompts import (
    construct_relevance_prompt,
    construct_coherence_prompt,
    construct_faithfulness_prompt,
    construct_must_not_prompt,
)


class DimensionScore(BaseModel):
    """Structured output schema for a single judge dimension."""
    score: int = Field(..., ge=1, le=5, description="Score from 1 (worst) to 5 (best)")
    justification: str = Field(..., description="1-2 sentence justification for the score")


class MustNotViolationResult(BaseModel):
    """Result for a single must_not_recommend constraint."""
    constraint_id: str = Field(..., description="Exact constraint_id from the input")
    violated: bool = Field(..., description="True if the response explicitly recommends the forbidden action")
    reasoning: str = Field(..., description="1 sentence explaining why this is or is not a violation")


class MustNotCheckResult(BaseModel):
    """Batched result for all must_not_recommend constraints in a task."""
    results: List[MustNotViolationResult] = Field(..., description="One entry per constraint checked")


class LLMJudge:
    """
    Evaluates LLM responses using GPT as judge.
    Each dimension (Relevance, Coherence, Faithfulness) is scored independently
    to avoid cross-dimension anchoring bias.
    """

    def __init__(self, judge_model, temperature: float = 0.0):
        """
        Args:
            judge_model: OpenAIModel instance used as judge
            temperature: Sampling temperature (0.0 = deterministic)
        """
        self.judge_model = judge_model
        self.temperature = temperature

    def evaluate_response(self, task, llm_response: str) -> Dict[str, Any]:
        """
        Evaluate a response across all three dimensions.

        Args:
            task: ReasoningTask object with prompt, match state, and reasoning elements
            llm_response: The response to evaluate

        Returns:
            Dict with per-dimension scores and overall judge score
        """
        try:
            relevance = self._score_relevance(task, llm_response)
            coherence = self._score_coherence(task, llm_response)
            faithfulness = self._score_faithfulness(task, llm_response)

            average = (relevance["score"] + coherence["score"] + faithfulness["score"]) / 3.0

            return {
                "relevance": relevance["score"],
                "relevance_justification": relevance["justification"],
                "coherence": coherence["score"],
                "coherence_justification": coherence["justification"],
                "faithfulness": faithfulness["score"],
                "faithfulness_justification": faithfulness["justification"],
                "judge_score": average,
                "success": True,
            }

        except Exception as e:
            print(f"Error in LLM judge evaluation: {e}")
            return {
                "relevance": 0.0,
                "relevance_justification": "",
                "coherence": 0.0,
                "coherence_justification": "",
                "faithfulness": 0.0,
                "faithfulness_justification": "",
                "judge_score": 0.0,
                "success": False,
            }

    def _score_dimension(self, prompt: str) -> Dict[str, Any]:
        """
        Call the judge with a structured output schema, returning score on 0-1 scale.

        Args:
            prompt: Fully constructed judge prompt for one dimension

        Returns:
            Dict with 'score' (0-1 scale) and 'justification' string
        """
        result: DimensionScore = self.judge_model.generate_structured(prompt, DimensionScore)
        return {
            "score": (result.score - 1) / 4.0,
            "justification": result.justification,
        }

    def _score_relevance(self, task, llm_response: str) -> Dict[str, Any]:
        return self._score_dimension(construct_relevance_prompt(task, llm_response))

    def _score_coherence(self, task, llm_response: str) -> Dict[str, Any]:
        return self._score_dimension(construct_coherence_prompt(task, llm_response))

    def _score_faithfulness(self, task, llm_response: str) -> Dict[str, Any]:
        return self._score_dimension(construct_faithfulness_prompt(task, llm_response))

    def check_must_not_violations(
        self, llm_response: str, must_not_constraints: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check all must_not_recommend constraints for a task in a single batched judge call.

        Args:
            llm_response: The response to evaluate
            must_not_constraints: List of constraint dicts with constraint_type == 'must_not_recommend'

        Returns:
            Dict with 'results' (list of per-constraint dicts) and 'success' bool
        """
        if not must_not_constraints:
            return {"results": [], "success": True}

        try:
            prompt = construct_must_not_prompt(llm_response, must_not_constraints)
            result: MustNotCheckResult = self.judge_model.generate_structured(prompt, MustNotCheckResult)

            return {
                "results": [
                    {
                        "constraint_id": r.constraint_id,
                        "violated": r.violated,
                        "reasoning": r.reasoning,
                    }
                    for r in result.results
                ],
                "success": True,
            }

        except Exception as e:
            print(f"Error in must_not_recommend judge check: {e}")
            # On failure, default to no violations (conservative — avoids false positives)
            return {
                "results": [
                    {
                        "constraint_id": c["constraint_id"],
                        "violated": False,
                        "reasoning": f"Judge check failed: {e}",
                    }
                    for c in must_not_constraints
                ],
                "success": False,
            }

    def evaluate_task(self, task, llm_response: str) -> Dict[str, Any]:
        """Alias for evaluate_response for consistency with ConstraintChecker API."""
        return self.evaluate_response(task, llm_response)
