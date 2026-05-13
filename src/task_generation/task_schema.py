"""
Task Schema for LoL Reasoning Benchmark
Defines the structure for reasoning tasks in Milestone 3
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ReasoningType(Enum):
    """Five reasoning modalities from Milestone 1 taxonomy"""

    STRATEGIC_PLANNING = "strategic_planning"
    CAUSAL_INFERENCE = "causal_inference"
    ERROR_DIAGNOSIS = "error_diagnosis"
    SPATIAL_REASONING = "spatial_reasoning"
    RESOURCE_LOGIC = "resource_logic"


class DifficultyLevel(Enum):
    """Reasoning depth levels"""

    BASIC = "basic"  # Single-factor reasoning
    INTERMEDIATE = "intermediate"  # Multi-factor reasoning
    ADVANCED = "advanced"  # Strategic chain reasoning


@dataclass
class ReasoningElement:
    """
    Expected reasoning component for LLM-as-judge evaluation.
    These come from the reasoning taxonomy (Milestone 1).
    """

    element_id: str
    name: str
    description: str
    importance: str  # 'required', 'expected', 'optional'


@dataclass
class GroundTruthConstraint:
    """
    Deterministic rule-based constraint from game reasoning rules (Milestone 1).
    Used for automated validation during evaluation (Milestone 4).
    """

    constraint_id: str
    constraint_type: (
        str  # 'must_mention', 'must_not_recommend', 'numeric_threshold', etc.
    )
    description: str
    parameters: Dict[str, Any]


@dataclass
class ReasoningTask:
    """
    Complete reasoning task for LLM evaluation.

    Each task includes:
    - The question/prompt
    - Compressed match context (from compactor)
    - Expected reasoning elements (for LLM-as-judge)
    - Ground truth constraints (for rule-based checks)
    """

    task_id: str
    reasoning_type: ReasoningType
    difficulty: DifficultyLevel

    # The actual task
    prompt: str
    compressed_match_state: str  # From LoL-MDC output

    # Match metadata
    match_id: str
    game_phase: str  # 'early', 'mid', 'late'
    timestamp_min: Optional[float] = None  # When in the match this scenario occurs

    # Evaluation criteria
    expected_reasoning_elements: List[ReasoningElement] = field(default_factory=list)
    ground_truth_constraints: List[GroundTruthConstraint] = field(default_factory=list)

    # Additional context
    tags: List[str] = field(
        default_factory=list
    )  # e.g., ['baron', 'gold_swing', 'comeback']
    notes: Optional[str] = None


@dataclass
class TaskDataset:
    """Collection of reasoning tasks for the benchmark"""

    dataset_id: str
    version: str
    tasks: List[ReasoningTask]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def save_to_file(self, filepath: str):
        """Save dataset to JSON file"""
        import json
        from pathlib import Path

        # Convert to dict
        dataset_dict = {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "metadata": self.metadata,
            "tasks": [],
        }

        for task in self.tasks:
            task_dict = {
                "task_id": task.task_id,
                "reasoning_type": task.reasoning_type.value,
                "difficulty": task.difficulty.value,
                "prompt": task.prompt,
                "compressed_match_state": task.compressed_match_state,
                "match_id": task.match_id,
                "game_phase": task.game_phase,
                "timestamp_min": task.timestamp_min,
                "expected_reasoning_elements": [
                    {
                        "element_id": elem.element_id,
                        "name": elem.name,
                        "description": elem.description,
                        "importance": elem.importance,
                    }
                    for elem in task.expected_reasoning_elements
                ],
                "ground_truth_constraints": [
                    {
                        "constraint_id": c.constraint_id,
                        "constraint_type": c.constraint_type,
                        "description": c.description,
                        "parameters": c.parameters,
                    }
                    for c in task.ground_truth_constraints
                ],
                "tags": task.tags,
                "notes": task.notes,
            }
            dataset_dict["tasks"].append(task_dict)

        # Save
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(dataset_dict, f, indent=2)

        print(f"✅ Saved {len(self.tasks)} tasks to {filepath}")

    @classmethod
    def load_from_file(cls, filepath: str) -> "TaskDataset":
        """Load dataset from JSON file"""
        import json

        with open(filepath, "r") as f:
            data = json.load(f)

        tasks = []
        for task_dict in data["tasks"]:
            task = ReasoningTask(
                task_id=task_dict["task_id"],
                reasoning_type=ReasoningType(task_dict["reasoning_type"]),
                difficulty=DifficultyLevel(task_dict["difficulty"]),
                prompt=task_dict["prompt"],
                compressed_match_state=task_dict["compressed_match_state"],
                match_id=task_dict["match_id"],
                game_phase=task_dict["game_phase"],
                timestamp_min=task_dict.get("timestamp_min"),
                expected_reasoning_elements=[
                    ReasoningElement(**elem)
                    for elem in task_dict["expected_reasoning_elements"]
                ],
                ground_truth_constraints=[
                    GroundTruthConstraint(**c)
                    for c in task_dict["ground_truth_constraints"]
                ],
                tags=task_dict.get("tags", []),
                notes=task_dict.get("notes"),
            )
            tasks.append(task)

        return cls(
            dataset_id=data["dataset_id"],
            version=data["version"],
            tasks=tasks,
            metadata=data.get("metadata", {}),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get dataset statistics"""
        from collections import Counter

        return {
            "total_tasks": len(self.tasks),
            "by_reasoning_type": dict(
                Counter(t.reasoning_type.value for t in self.tasks)
            ),
            "by_difficulty": dict(Counter(t.difficulty.value for t in self.tasks)),
            "by_phase": dict(Counter(t.game_phase for t in self.tasks)),
            "unique_matches": len(set(t.match_id for t in self.tasks)),
        }
