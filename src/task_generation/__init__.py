"""
Task Generation Module for LoL Reasoning Benchmark (Milestone 3)

This module handles pattern detection and task generation from compressed matches.
"""

from .task_schema import (
    ReasoningType,
    DifficultyLevel,
    ReasoningElement,
    GroundTruthConstraint,
    ReasoningTask,
    TaskDataset,
)

from .pattern_detectors import (
    PatternDetector,
    BaronContestDetector,
    ObjectiveTradeDetector,
    GoldSwingDetector,
    BadBaronAttemptDetector,
    get_all_detectors,
    detect_all_patterns,
)

from .task_templates import (
    TaskTemplate,
    BaronContestTemplate,
    ObjectiveTradeTemplate,
    GoldSwingTemplate,
    BadBaronTemplate,
    get_template,
    TEMPLATE_REGISTRY,
)

__all__ = [
    # Enums and data structures
    "ReasoningType",
    "DifficultyLevel",
    "ReasoningElement",
    "GroundTruthConstraint",
    "ReasoningTask",
    "TaskDataset",
    # Pattern detectors
    "PatternDetector",
    "BaronContestDetector",
    "ObjectiveTradeDetector",
    "GoldSwingDetector",
    "BadBaronAttemptDetector",
    "get_all_detectors",
    "detect_all_patterns",
    # Templates
    "TaskTemplate",
    "BaronContestTemplate",
    "ObjectiveTradeTemplate",
    "GoldSwingTemplate",
    "BadBaronTemplate",
    "get_template",
    "TEMPLATE_REGISTRY",
]
