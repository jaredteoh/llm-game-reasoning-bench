"""
Task Templates for Milestone 3

Each template converts a detected pattern opportunity into a complete ReasoningTask.
Templates include:
- Prompt template (with variables)
- Expected reasoning elements
- Ground truth constraints
"""

from typing import Dict, Any
from .task_schema import (
    ReasoningTask,
    ReasoningType,
    DifficultyLevel,
    ReasoningElement,
    GroundTruthConstraint,
)


class TaskTemplate:
    """Base class for task templates"""

    def __init__(self, template_id: str, reasoning_type: ReasoningType):
        self.template_id = template_id
        self.reasoning_type = reasoning_type

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:
        """
        Create a complete task from an opportunity.

        Args:
            opportunity: Pattern detection result
            compressed_match_state: Full compressed match text
            match_id: Match ID

        Returns:
            Complete ReasoningTask object
        """
        raise NotImplementedError


# ============================================================================
# STRATEGIC PLANNING TEMPLATES
# ============================================================================


class BaronContestTemplate(TaskTemplate):
    """Template for Baron contest decision tasks"""

    def __init__(self):
        super().__init__("baron_contest", ReasoningType.STRATEGIC_PLANNING)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        team = opportunity["team"]
        timestamp = opportunity["timestamp"]
        gold_diff = opportunity["gold_diff"]
        phase = opportunity["phase"]

        # Build prompt
        if gold_diff > 0:
            gold_desc = f"ahead by {abs(gold_diff):,} gold"
        elif gold_diff < 0:
            gold_desc = f"behind by {abs(gold_diff):,} gold"
        else:
            gold_desc = "at even gold"

        prompt = (
            f"{team} team is {gold_desc} at {timestamp:.1f} minutes. "
            f"Should they attempt Baron Nashor? "
            f"Explain your strategic reasoning considering team compositions, "
            f"gold state, vision control, and risks."
        )

        # Expected reasoning elements
        reasoning_elements = [
            ReasoningElement(
                element_id="risk_assessment",
                name="Risk-Reward Analysis",
                description="Evaluates risks of Baron attempt vs. rewards if successful",
                importance="required",
            ),
            ReasoningElement(
                element_id="gold_consideration",
                name="Gold State Analysis",
                description="Considers current gold advantage/disadvantage",
                importance="required",
            ),
            ReasoningElement(
                element_id="vision_control",
                name="Vision Control",
                description="Mentions need for vision/control around Baron",
                importance="expected",
            ),
            ReasoningElement(
                element_id="alternative_options",
                name="Alternative Options",
                description="Suggests alternatives to Baron (towers, dragons, etc.)",
                importance="expected",
            ),
        ]

        # Ground truth constraints
        constraints = [
            GroundTruthConstraint(
                constraint_id="baron_vision_requirement",
                constraint_type="must_mention",
                description="Must mention vision control when discussing Baron",
                parameters={
                    "keywords": ["vision", "control", "ward", "see", "sight"],
                    "min_mentions": 1,
                },
            )
        ]

        # Add constraint for severe deficit (shouldn't recommend)
        if gold_diff < -8000:
            constraints.append(
                GroundTruthConstraint(
                    constraint_id="baron_severe_deficit_no_recommend",
                    constraint_type="must_not_recommend",
                    description="Should not recommend Baron when 8k+ gold behind",
                    parameters={
                        "forbidden_recommendations": [
                            "start baron",
                            "do baron",
                            "take baron immediately",
                            "go for baron now",
                        ]
                    },
                )
            )

        if gold_diff < -10000:  # 10k+ behind
            constraints.append(
                GroundTruthConstraint(
                    constraint_id="baron_massive_deficit_critical",
                    constraint_type="must_not_recommend",
                    description="Must not recommend Baron when 10k+ behind",
                    parameters={
                        "forbidden_recommendations": [
                            "start baron",
                            "do baron",
                            "take baron",
                            "go for baron",
                            "attempt baron",
                        ]
                    },
                )
            )
        elif gold_diff < -3000:  # Moderately behind
            constraints.append(
                GroundTruthConstraint(
                    constraint_id="no_blind_baron_behind",
                    constraint_type="must_not_recommend",
                    description="Must not recommend Baron without vision when behind",
                    parameters={
                        "forbidden_recommendations": [
                            "go baron without vision",
                            "start baron blind",
                            "do baron without wards",
                        ]
                    },
                )
            )

        # Determine difficulty
        if abs(gold_diff) < 2000:
            difficulty = DifficultyLevel.INTERMEDIATE  # Close game = harder decision
        elif abs(gold_diff) > 6000:
            difficulty = DifficultyLevel.BASIC  # Clear advantage/disadvantage
        else:
            difficulty = DifficultyLevel.INTERMEDIATE

        # Create task
        task = ReasoningTask(
            task_id=f"SP_baron_{match_id}_{int(timestamp)}",
            reasoning_type=self.reasoning_type,
            difficulty=difficulty,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            timestamp_min=timestamp,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["baron", "strategic_planning", "objective_decision"],
            notes=f"Baron contest at {timestamp:.1f}m with {gold_diff:+,} gold diff",
        )

        return task


class ObjectiveTradeTemplate(TaskTemplate):
    """Template for objective trade evaluation tasks"""

    def __init__(self):
        super().__init__("objective_trade", ReasoningType.STRATEGIC_PLANNING)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        timestamp = opportunity["timestamp"]
        blue_gained = opportunity["blue_gained"]
        red_gained = opportunity["red_gained"]
        phase = opportunity["phase"]

        # Helper function to format objective names
        def format_objective(obj_name):
            """Format objective names to be more readable"""
            # Remove underscores and format nicely
            formatted = obj_name.replace("_", " ").title()

            # Shorten common names
            formatted = formatted.replace("Tower Building", "Tower")
            formatted = formatted.replace("Inhibitor Building", "Inhibitor")

            return formatted

        def is_high_value(obj_list):
            """Check if list contains Baron/Inhibitor/Elder"""
            high_value = ["BARON", "INHIBITOR", "ELDER"]
            return any(hv in str(obj_list) for hv in high_value)

        def is_low_value(obj_list):
            """Check if list only contains towers"""
            return "TOWER" in str(obj_list) and not is_high_value(obj_list)

        constraints = [
            GroundTruthConstraint(
                constraint_id="mentions_both_sides",
                constraint_type="must_mention",
                description="Must mention what both teams gained",
                parameters={
                    "must_include": ["blue", "red"],
                    "context": "when evaluating trade",
                },
            )
        ]

        # Check trade balance
        blue_has_baron = is_high_value(blue_gained)
        red_has_baron = is_high_value(red_gained)
        blue_only_tower = is_low_value(blue_gained)
        red_only_tower = is_low_value(red_gained)

        # Add critical constraint if trade is clearly one-sided
        if blue_has_baron and red_only_tower:
            constraints.append(
                GroundTruthConstraint(
                    constraint_id="baron_vs_tower_critical",
                    constraint_type="must_not_recommend",
                    description="Must recognize Baron >> Tower",
                    parameters={
                        "forbidden_recommendations": [
                            "red got better",
                            "red won",
                            "even trade",
                            "fair trade",
                        ]
                    },
                )
            )
        elif red_has_baron and blue_only_tower:
            constraints.append(
                GroundTruthConstraint(
                    constraint_id="baron_vs_tower_critical",
                    constraint_type="must_not_recommend",
                    description="Must recognize Baron >> Tower",
                    parameters={
                        "forbidden_recommendations": [
                            "blue got better",
                            "blue won",
                            "even trade",
                            "fair trade",
                        ]
                    },
                )
            )

        # Format objective lists
        blue_str = ", ".join(format_objective(obj) for obj in blue_gained[:3])
        red_str = ", ".join(format_objective(obj) for obj in red_gained[:3])

        prompt = (
            f"Around {timestamp} minutes, Blue team took {blue_str} while "
            f"Red team took {red_str}. "
            f"Which team got the better trade? Explain your reasoning considering "
            f"objective values, map control, and game state."
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="objective_valuation",
                name="Objective Value Comparison",
                description="Compares relative value of objectives traded",
                importance="required",
            ),
            ReasoningElement(
                element_id="map_control_impact",
                name="Map Control Analysis",
                description="Considers how trade affects map control",
                importance="expected",
            ),
            ReasoningElement(
                element_id="tempo_consideration",
                name="Tempo Analysis",
                description="Evaluates tempo/timing implications",
                importance="optional",
            ),
        ]

        task = ReasoningTask(
            task_id=f"SP_trade_{match_id}_{timestamp}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.INTERMEDIATE,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            timestamp_min=float(timestamp),
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["objective_trade", "strategic_planning", "resource_logic"],
            notes=f"Trade: Blue {blue_str} vs Red {red_str}",
        )

        return task


# ============================================================================
# CAUSAL INFERENCE TEMPLATES
# ============================================================================


class GoldSwingTemplate(TaskTemplate):
    """Template for gold swing explanation tasks"""

    def __init__(self):
        super().__init__("gold_swing", ReasoningType.CAUSAL_INFERENCE)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        phase_start = opportunity["phase_start"]
        phase_end = opportunity["phase_end"]
        gold_start = opportunity["gold_diff_start"]
        gold_end = opportunity["gold_diff_end"]
        swing = opportunity["swing_amount"]

        # Format gold values
        prompt = (
            f"Between {phase_start} and {phase_end} game, there was a {swing:,} gold swing. "
            f"The gold difference went from {gold_start:+,} to {gold_end:+,}. "
            f"What caused this reversal? Explain the causal chain of events."
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="primary_cause",
                name="Primary Cause Identification",
                description="Identifies the main event that triggered the swing",
                importance="required",
            ),
            ReasoningElement(
                element_id="causal_chain",
                name="Causal Chain Tracing",
                description="Explains how initial event led to subsequent outcomes",
                importance="required",
            ),
            ReasoningElement(
                element_id="contributing_factors",
                name="Contributing Factors",
                description="Acknowledges secondary factors that amplified the swing",
                importance="expected",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="identifies_specific_events",
                constraint_type="must_mention",
                description="Must reference specific game events (teamfights, objectives)",
                parameters={
                    "keywords": [
                        "teamfight",
                        "fight",
                        "dragon",
                        "baron",
                        "tower",
                        "inhibitor",
                        "ace",
                        "kill",
                    ],
                    "min_mentions": 2,
                },
            )
        ]

        # Difficulty based on swing size
        if swing > 5000:
            difficulty = DifficultyLevel.INTERMEDIATE
        else:
            difficulty = DifficultyLevel.BASIC

        task = ReasoningTask(
            task_id=f"CI_swing_{match_id}_{phase_start}_{phase_end}",
            reasoning_type=self.reasoning_type,
            difficulty=difficulty,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase_end,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["gold_swing", "causal_inference", "comeback"],
            notes=f"{swing:,} gold swing from {phase_start} to {phase_end}",
        )

        return task


class SnowballEffectTemplate(TaskTemplate):
    """Template for snowball effect causal reasoning"""

    def __init__(self):
        super().__init__("snowball_effect", ReasoningType.CAUSAL_INFERENCE)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        team = opportunity["team"]
        early_lead = opportunity["early_lead"]
        mid_lead = opportunity["mid_lead"]
        amplification = opportunity["amplification"]
        phase_start = opportunity["phase_start"]
        phase_end = opportunity["phase_end"]

        # Determine timestamp ranges
        if phase_start == "early":
            start_time = "10 minutes"
        else:
            start_time = "20 minutes"

        if phase_end == "mid":
            end_time = "20 minutes"
        else:
            end_time = "30 minutes"

        prompt = (
            f"{team} team had a {early_lead:,} gold lead at {start_time}, "
            f"which grew to {mid_lead:,} gold by {end_time}. "
            f"Trace the causal chain that allowed this {amplification:,} gold "
            f"amplification. How did the initial advantage compound?"
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="initial_advantage",
                name="Initial Advantage Identification",
                description="Identifies what created the early lead",
                importance="required",
            ),
            ReasoningElement(
                element_id="compounding_mechanism",
                name="Compounding Mechanism",
                description="Explains how advantage led to more advantages (map control → objectives → gold → items)",
                importance="required",
            ),
            ReasoningElement(
                element_id="causal_steps",
                name="Step-by-Step Causation",
                description="Traces the specific sequence: A caused B, which enabled C, etc.",
                importance="required",
            ),
            ReasoningElement(
                element_id="enemy_response",
                name="Enemy Response Failure",
                description="Considers why the losing team couldn't stop the snowball",
                importance="expected",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="mentions_multiple_events",
                constraint_type="must_mention",
                description="Must reference multiple events in the causal chain",
                parameters={
                    "keywords": [
                        "tower",
                        "dragon",
                        "baron",
                        "inhibitor",
                        "teamfight",
                        "objective",
                        "pressure",
                        "control",
                    ],
                    "min_mentions": 3,
                },
            ),
            GroundTruthConstraint(
                constraint_id="explains_compounding",
                constraint_type="must_mention",
                description="Must explain how advantages compound",
                parameters={
                    "keywords": [
                        "led to",
                        "enabled",
                        "allowed",
                        "because",
                        "then",
                        "which",
                        "snowball",
                        "compound",
                    ],
                    "min_mentions": 2,
                },
            ),
        ]

        task = ReasoningTask(
            task_id=f"CI_snowball_{match_id}_{phase_start}_{phase_end}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.INTERMEDIATE,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase_end,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["causal_inference", "snowball", "advantage_compound"],
            notes=f"{team} snowballed {early_lead:,}g → {mid_lead:,}g ({amplification:,}g gain)",
        )

        return task


class ComebackMechanicTemplate(TaskTemplate):
    """Template for comeback mechanic causal reasoning"""

    def __init__(self):
        super().__init__("comeback_mechanic", ReasoningType.CAUSAL_INFERENCE)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        team = opportunity["team"]
        initial_deficit = opportunity["initial_deficit"]
        final_state = opportunity["final_state"]
        recovery = opportunity["recovery_amount"]
        phase_start = opportunity["phase_start"]
        phase_end = opportunity["phase_end"]

        # Determine timestamp ranges
        if phase_start == "early":
            start_time = "10 minutes"
        else:
            start_time = "20 minutes"

        if phase_end == "mid":
            end_time = "20 minutes"
        else:
            end_time = "30 minutes"

        # Format final state
        if final_state <= 1000 and final_state >= -1000:
            final_desc = "even gold"
        elif final_state > 1000:
            final_desc = f"{final_state:,} gold ahead"
        else:
            final_desc = f"{abs(final_state):,} gold behind"

        prompt = (
            f"{team} team was {initial_deficit:,} gold behind at {start_time}, "
            f"but recovered to {final_desc} by {end_time}. "
            f"What sequence of events enabled this {recovery:,} gold recovery? "
            f"Trace the causal factors that turned the game around."
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="turning_point",
                name="Turning Point Identification",
                description="Identifies the key event(s) that started the comeback",
                importance="required",
            ),
            ReasoningElement(
                element_id="comeback_mechanics",
                name="Comeback Mechanics",
                description="Explains specific comeback mechanics (bounties, scaling, punishing mistakes)",
                importance="required",
            ),
            ReasoningElement(
                element_id="causal_sequence",
                name="Causal Sequence",
                description="Traces how one success led to another",
                importance="required",
            ),
            ReasoningElement(
                element_id="enemy_mistakes",
                name="Enemy Mistakes",
                description="Identifies mistakes by the leading team that enabled comeback",
                importance="expected",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="identifies_key_events",
                constraint_type="must_mention",
                description="Must identify specific events that enabled comeback",
                parameters={
                    "keywords": [
                        "teamfight",
                        "objective",
                        "baron",
                        "dragon",
                        "tower",
                        "ace",
                        "shutdown",
                        "bounty",
                    ],
                    "min_mentions": 2,
                },
            ),
            GroundTruthConstraint(
                constraint_id="explains_causation",
                constraint_type="must_mention",
                description="Must explain how events caused the comeback",
                parameters={
                    "keywords": [
                        "because",
                        "led to",
                        "enabled",
                        "allowed",
                        "then",
                        "caused",
                        "resulted in",
                    ],
                    "min_mentions": 2,
                },
            ),
        ]

        task = ReasoningTask(
            task_id=f"CI_comeback_{match_id}_{phase_start}_{phase_end}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.INTERMEDIATE,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase_end,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["causal_inference", "comeback", "reversal"],
            notes=f"{team} recovered {recovery:,}g from {initial_deficit:,}g deficit",
        )

        return task


# ============================================================================
# ERROR DIAGNOSIS TEMPLATES
# ============================================================================


class BadBaronTemplate(TaskTemplate):
    """Template for diagnosing bad Baron attempts"""

    def __init__(self):
        super().__init__("bad_baron", ReasoningType.ERROR_DIAGNOSIS)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        team = opportunity["team"]
        timestamp = opportunity["timestamp"]
        gold_deficit = opportunity["gold_deficit"]
        phase = opportunity["phase"]

        prompt = (
            f"{team} team attempted Baron at {timestamp:.1f} minutes while "
            f"{gold_deficit:,} gold behind. "
            f"Identify the strategic error in this decision and explain what "
            f"they should have done instead."
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="error_identification",
                name="Error Identification",
                description="Clearly identifies why the Baron attempt was a mistake",
                importance="required",
            ),
            ReasoningElement(
                element_id="alternative_action",
                name="Better Alternative",
                description="Proposes what team should have done instead",
                importance="required",
            ),
            ReasoningElement(
                element_id="severity_assessment",
                name="Error Severity",
                description="Assesses how critical this mistake was",
                importance="expected",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="recognizes_as_mistake",
                constraint_type="must_not_recommend",
                description="Must not defend the Baron attempt as correct",
                parameters={
                    "forbidden_statements": [
                        "was the right call",
                        "good decision",
                        "correct play",
                        "should have done baron",
                    ]
                },
            ),
            GroundTruthConstraint(
                constraint_id="mentions_gold_deficit",
                constraint_type="must_mention",
                description="Must acknowledge the gold deficit as a factor",
                parameters={
                    "keywords": ["behind", "deficit", "disadvantage", "gold"],
                    "min_mentions": 1,
                },
            ),
        ]

        task = ReasoningTask(
            task_id=f"ED_baron_{match_id}_{int(timestamp)}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.BASIC,  # Clear mistake = easier to diagnose
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            timestamp_min=timestamp,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["error_diagnosis", "baron", "bad_decision"],
            notes=f"Bad Baron attempt: {gold_deficit:,} gold behind",
        )

        return task


class BadTeamfightTemplate(TaskTemplate):
    """Template for bad teamfight error diagnosis"""

    def __init__(self):
        super().__init__("bad_teamfight", ReasoningType.ERROR_DIAGNOSIS)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        team = opportunity["team"]
        phase = opportunity["phase"]
        gold_swing = opportunity["gold_swing"]
        deficit = opportunity["resulting_deficit"]

        prompt = (
            f"During {phase} game, {team} team lost {abs(gold_swing):,} gold advantage, "
            f"resulting in a {deficit:,} gold deficit. "
            f"Diagnose what strategic error likely occurred. "
            f"What should they have done differently to avoid this outcome?"
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="error_identification",
                name="Error Identification",
                description="Identifies the likely strategic mistake (bad fight, overextension, etc.)",
                importance="required",
            ),
            ReasoningElement(
                element_id="causal_analysis",
                name="Causal Analysis",
                description="Explains why this decision was wrong given game state",
                importance="required",
            ),
            ReasoningElement(
                element_id="alternative_action",
                name="Better Alternative",
                description="Proposes what team should have done instead",
                importance="required",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="acknowledges_mistake",
                constraint_type="must_mention",
                description="Must acknowledge this was a strategic error",
                parameters={
                    "keywords": [
                        "mistake",
                        "error",
                        "should not",
                        "avoid",
                        "wrong",
                        "bad",
                    ],
                    "min_mentions": 1,
                },
            )
        ]

        task = ReasoningTask(
            task_id=f"ED_teamfight_{match_id}_{phase}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.INTERMEDIATE,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["error_diagnosis", "teamfight", "gold_swing"],
            notes=f"{team} lost {abs(gold_swing):,} gold in {phase} game",
        )

        return task


class OverextensionTemplate(TaskTemplate):
    """Template for overextension error diagnosis"""

    def __init__(self):
        super().__init__("overextension", ReasoningType.ERROR_DIAGNOSIS)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        team = opportunity["team"]
        timestamp = opportunity["timestamp"]
        phase = opportunity["phase"]
        lost = opportunity["lost"]
        gained = opportunity.get("gained", [])

        # Format structure names
        def format_structure(struct_type):
            return struct_type.replace("_", " ").title().replace(" Building", "")

        lost_str = ", ".join(format_structure(s) for s in lost[:2])
        gained_str = (
            ", ".join(format_structure(s) for s in gained[:2]) if gained else "nothing"
        )

        prompt = (
            f"Around {timestamp} minutes, {team} team lost {lost_str} "
            f"while only gaining {gained_str} in return. "
            f"Diagnose the macro error that led to this unfavorable trade. "
            f"What map awareness mistake was made?"
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="macro_error",
                name="Macro Error Identification",
                description="Identifies the map positioning/awareness mistake",
                importance="required",
            ),
            ReasoningElement(
                element_id="consequence_analysis",
                name="Consequence Analysis",
                description="Explains why this trade was unfavorable",
                importance="required",
            ),
            ReasoningElement(
                element_id="prevention_strategy",
                name="Prevention Strategy",
                description="Suggests how to avoid similar mistakes (vision, communication, etc.)",
                importance="expected",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="mentions_map_awareness",
                constraint_type="must_mention",
                description="Must reference map awareness or positioning",
                parameters={
                    "keywords": [
                        "map",
                        "awareness",
                        "position",
                        "overextend",
                        "vision",
                        "track",
                    ],
                    "min_mentions": 1,
                },
            )
        ]

        task = ReasoningTask(
            task_id=f"ED_overextension_{match_id}_{timestamp}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.INTERMEDIATE,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            timestamp_min=float(timestamp),
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["error_diagnosis", "overextension", "map_awareness"],
            notes=f"{team} overextended at {timestamp}m",
        )

        return task


class MissedObjectiveTemplate(TaskTemplate):
    """Template for missed objective opportunity diagnosis"""

    def __init__(self):
        super().__init__("missed_objective", ReasoningType.ERROR_DIAGNOSIS)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        missed_team = opportunity["missed_team"]
        actual_team = opportunity["actual_team"]
        timestamp = opportunity["timestamp"]
        phase = opportunity["phase"]
        objective = opportunity["objective"]
        gold_advantage = opportunity["gold_advantage"]

        prompt = (
            f"{missed_team} team was {gold_advantage:,} gold ahead but allowed "
            f"{actual_team} team to secure {objective} at {timestamp:.1f} minutes. "
            f"Diagnose the error in game sense and objective prioritization. "
            f"Why did the winning team fail to capitalize on their advantage?"
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="opportunity_recognition",
                name="Opportunity Recognition Failure",
                description="Identifies that team failed to recognize objective timing",
                importance="required",
            ),
            ReasoningElement(
                element_id="priority_error",
                name="Priority Error",
                description="Explains what they prioritized instead (incorrectly)",
                importance="required",
            ),
            ReasoningElement(
                element_id="correct_priority",
                name="Correct Priority",
                description="States they should have prioritized the objective",
                importance="required",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="should_have_taken_objective",
                constraint_type="must_mention",
                description="Must indicate team should have taken the objective",
                parameters={
                    "keywords": [
                        "should have",
                        "missed",
                        "opportunity",
                        "priority",
                        "take",
                        "secure",
                    ],
                    "min_mentions": 1,
                },
            )
        ]

        task = ReasoningTask(
            task_id=f"ED_missed_{match_id}_{int(timestamp)}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.INTERMEDIATE,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            timestamp_min=timestamp,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["error_diagnosis", "missed_opportunity", "objective_priority"],
            notes=f"{missed_team} missed {objective} at {timestamp:.1f}m with {gold_advantage:,}g advantage",
        )

        return task


# ============================================================================
# EARLY GAME TEMPLATES
# ============================================================================


class FirstDrakeContestTemplate(TaskTemplate):
    """Template for first dragon contest decisions"""

    def __init__(self):
        super().__init__("first_drake_contest", ReasoningType.STRATEGIC_PLANNING)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        team = opportunity["team"]
        timestamp = opportunity["timestamp"]
        drake_type = opportunity["drake_type"]
        gold_diff = opportunity["gold_diff"]
        phase = opportunity["phase"]

        # Build prompt
        prompt = (
            f"At {timestamp:.1f} minutes, the first dragon ({drake_type}) spawns. "
            f"Should {team} team prioritize contesting this dragon? "
            f"Consider the early game gold state, vision control, lane priority, "
            f"and trade-offs with other objectives."
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="early_priority",
                name="Early Priority Assessment",
                description="Evaluates drake value vs. other early objectives",
                importance="required",
            ),
            ReasoningElement(
                element_id="lane_state",
                name="Lane State Analysis",
                description="Considers which lanes have priority for rotation",
                importance="required",
            ),
            ReasoningElement(
                element_id="vision_setup",
                name="Vision Setup",
                description="Discusses vision control needed for drake contest",
                importance="expected",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="early_game_context",
                constraint_type="must_mention",
                description="Must acknowledge this is early game decision",
                parameters={
                    "keywords": ["early", "lane", "level", "priority"],
                    "min_mentions": 1,
                },
            )
        ]

        # Don't contest drake heavily outnumbered
        constraints.append(
            GroundTruthConstraint(
                constraint_id="no_outnumbered_drake",
                constraint_type="must_not_recommend",
                description="Must not contest drake when heavily outnumbered",
                parameters={
                    "forbidden_recommendations": [
                        "contest 3v5",
                        "fight outnumbered",
                        "contest anyway",
                        "just go in",
                    ]
                },
            )
        )

        task = ReasoningTask(
            task_id=f"SP_first_drake_{match_id}_{int(timestamp)}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.INTERMEDIATE,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            timestamp_min=timestamp,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["early_game", "dragon", "strategic_planning", "priority"],
            notes=f"First drake at {timestamp:.1f}m",
        )

        return task


# ============================================================================
# SPATIAL REASONING TEMPLATES
# ============================================================================


class SplitPushTemplate(TaskTemplate):
    """Template for split push spatial reasoning tasks"""

    def __init__(self):
        super().__init__("split_push", ReasoningType.SPATIAL_REASONING)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        timestamp = opportunity["timestamp"]
        lanes = opportunity["lanes_pressured"]
        phase = opportunity["phase"]

        prompt = (
            f"Around {timestamp} minutes, there is pressure in {len(lanes)} different lanes "
            f"({', '.join(lanes)}). "
            f"Analyze the map positioning and explain which team has better macro control. "
            f"Should the defending team group to contest or match the split push?"
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="map_positioning",
                name="Map Positioning Analysis",
                description="Evaluates spatial distribution of pressure across lanes",
                importance="required",
            ),
            ReasoningElement(
                element_id="rotation_timing",
                name="Rotation Timing",
                description="Considers travel time and rotation decisions",
                importance="required",
            ),
            ReasoningElement(
                element_id="threat_prioritization",
                name="Threat Prioritization",
                description="Identifies which lane threat is most critical",
                importance="expected",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="mentions_multiple_lanes",
                constraint_type="must_mention",
                description="Must acknowledge pressure in multiple lanes",
                parameters={
                    "keywords": ["lane", "split", "pressure", "map", "rotation"],
                    "min_mentions": 2,
                },
            )
        ]

        # Never recommend defending outnumbered
        constraints.append(
            GroundTruthConstraint(
                constraint_id="no_outnumbered_defense",
                constraint_type="must_not_recommend",
                description="Must not recommend defending 1v5",
                parameters={
                    "forbidden_recommendations": [
                        "defend 1v5",
                        "hold alone",
                        "defend outnumbered",
                        "fight them solo",
                        "1v5 is fine",
                    ]
                },
            )
        )

        task = ReasoningTask(
            task_id=f"SR_split_{match_id}_{timestamp}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.INTERMEDIATE,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            timestamp_min=float(timestamp),
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["spatial_reasoning", "split_push", "map_control"],
            notes=f"Split push across {len(lanes)} lanes",
        )

        return task


class MapControlTemplate(TaskTemplate):
    """Template for map control disparity tasks"""

    def __init__(self):
        super().__init__("map_control_disparity", ReasoningType.SPATIAL_REASONING)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        timestamp = opportunity["timestamp"]
        controlling_team = opportunity["controlling_team"]
        phase = opportunity["phase"]

        prompt = (
            f"{controlling_team} team has established map control across all three lanes "
            f"by {timestamp:.1f} minutes. "
            f"Analyze the spatial advantages this provides and explain how the losing team "
            f"should approach regaining map presence."
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="spatial_advantage",
                name="Spatial Advantage Assessment",
                description="Identifies map control benefits (vision, rotation, pressure)",
                importance="required",
            ),
            ReasoningElement(
                element_id="comeback_positioning",
                name="Comeback Positioning",
                description="Suggests spatial strategy for losing team",
                importance="required",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="map_control_mention",
                constraint_type="must_mention",
                description="Must discuss map control and positioning",
                parameters={
                    "keywords": ["map", "control", "vision", "position", "territory"],
                    "min_mentions": 2,
                },
            )
        ]

        task = ReasoningTask(
            task_id=f"SR_mapcontrol_{match_id}_{int(timestamp)}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.ADVANCED,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            timestamp_min=timestamp,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["spatial_reasoning", "map_control", "comeback"],
            notes=f"{controlling_team} controls all lanes at {timestamp}m",
        )

        return task


# ============================================================================
# RESOURCE LOGIC TEMPLATES
# ============================================================================


class PowerSpikeTemplate(TaskTemplate):
    """Template for power spike timing tasks"""

    def __init__(self):
        super().__init__("power_spike_timing", ReasoningType.RESOURCE_LOGIC)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        team = opportunity["team"]
        team_gold = opportunity["team_gold"]
        gold_diff = opportunity["gold_diff"]
        phase = opportunity["phase"]
        spike_type = opportunity["spike_type"]

        gold_state = (
            "ahead"
            if (team == "Blue" and gold_diff > 0) or (team == "Red" and gold_diff < 0)
            else "behind"
        )

        prompt = (
            f"{team} team has reached approximately {team_gold:,} total gold "
            f"(currently {abs(gold_diff):,} gold {gold_state}). "
            f"Should they force fights/objectives now to capitalize on item power spikes, "
            f"or continue farming for their next power spike? "
            f"Explain the resource logic behind your decision."
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="power_spike_timing",
                name="Power Spike Timing",
                description="Recognizes current and next power spike windows",
                importance="required",
            ),
            ReasoningElement(
                element_id="resource_optimization",
                name="Resource Optimization",
                description="Weighs immediate action vs. continued farming",
                importance="required",
            ),
            ReasoningElement(
                element_id="opponent_scaling",
                name="Opponent Scaling Consideration",
                description="Considers enemy team's scaling and power spikes",
                importance="expected",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="mentions_items_or_gold",
                constraint_type="must_mention",
                description="Must reference gold/items/power in reasoning",
                parameters={
                    "keywords": ["item", "gold", "power", "spike", "scale", "damage"],
                    "min_mentions": 2,
                },
            )
        ]

        task = ReasoningTask(
            task_id=f"RL_powerspike_{match_id}_{phase}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.INTERMEDIATE,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["resource_logic", "power_spike", "timing"],
            notes=f"{team} at {spike_type}",
        )

        return task


class ScalingDecisionTemplate(TaskTemplate):
    """Template for scaling vs. fighting decisions"""

    def __init__(self):
        super().__init__("scaling_decision", ReasoningType.RESOURCE_LOGIC)

    def create_task(
        self, opportunity: Dict[str, Any], compressed_match_state: str, match_id: str
    ) -> ReasoningTask:

        team = opportunity["team"]
        early_deficit = opportunity["early_deficit"]
        mid_deficit = opportunity["mid_deficit"]
        phase = opportunity["phase"]

        prompt = (
            f"{team} team was {early_deficit:,} gold behind in early game "
            f"and is still {mid_deficit:,} gold behind in mid game. "
            f"Should they continue avoiding fights to scale, or force action to stop "
            f"the bleeding? Explain the resource management logic."
        )

        reasoning_elements = [
            ReasoningElement(
                element_id="scaling_assessment",
                name="Scaling Assessment",
                description="Evaluates whether team composition favors scaling",
                importance="required",
            ),
            ReasoningElement(
                element_id="deficit_management",
                name="Deficit Management",
                description="Analyzes whether deficit is stabilizing or growing",
                importance="required",
            ),
            ReasoningElement(
                element_id="timing_windows",
                name="Timing Windows",
                description="Identifies when team needs to act vs. when they can delay",
                importance="expected",
            ),
        ]

        constraints = [
            GroundTruthConstraint(
                constraint_id="addresses_scaling",
                constraint_type="must_mention",
                description="Must discuss scaling and timing concepts",
                parameters={
                    "keywords": ["scale", "scaling", "late", "time", "farm", "delay"],
                    "min_mentions": 1,
                },
            )
        ]

        task = ReasoningTask(
            task_id=f"RL_scaling_{match_id}_{phase}",
            reasoning_type=self.reasoning_type,
            difficulty=DifficultyLevel.ADVANCED,
            prompt=prompt,
            compressed_match_state=compressed_match_state,
            match_id=match_id,
            game_phase=phase,
            expected_reasoning_elements=reasoning_elements,
            ground_truth_constraints=constraints,
            tags=["resource_logic", "scaling", "deficit_management"],
            notes=f"{team} managing deficit: {early_deficit}→{mid_deficit}",
        )

        return task


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

TEMPLATE_REGISTRY = {
    # Strategic Planning
    "baron_contest": BaronContestTemplate(),
    "objective_trade": ObjectiveTradeTemplate(),
    "first_drake_contest": FirstDrakeContestTemplate(),
    # Causal Inference
    "gold_swing": GoldSwingTemplate(),
    "snowball_effect": SnowballEffectTemplate(),
    "comeback_mechanic": ComebackMechanicTemplate(),
    # Error Diagnosis
    "bad_baron_attempt": BadBaronTemplate(),
    "bad_teamfight": BadTeamfightTemplate(),
    "overextension": OverextensionTemplate(),
    "missed_objective": MissedObjectiveTemplate(),
    # Spatial Reasoning
    "split_push": SplitPushTemplate(),
    "map_control_disparity": MapControlTemplate(),
    # Resource Logic
    "power_spike_timing": PowerSpikeTemplate(),
    "scaling_decision": ScalingDecisionTemplate(),
}


def get_template(pattern_type: str) -> TaskTemplate:
    """Get template for a pattern type"""
    return TEMPLATE_REGISTRY.get(pattern_type)
