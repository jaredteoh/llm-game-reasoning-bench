"""
Pattern Detectors for Task Generation (Milestone 3)

Each detector identifies interesting strategic scenarios from compressed match data.
These patterns correspond to the 5 reasoning types from Milestone 1.
"""

from typing import List, Dict, Any, Optional


class PatternDetector:
    """Base class for pattern detection"""

    def __init__(self, name: str, reasoning_type: str):
        self.name = name
        self.reasoning_type = reasoning_type

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect pattern instances in a match.

        Args:
            compressed_match: Dict containing:
                - compressed_text: str (output from compactor)
                - match_id: str
                - strategic_events: List[Dict] (from compactor)
                - phase_summaries: Dict[str, Dict] (from compactor)

        Returns:
            List of opportunity dicts, each containing context for task generation
        """
        raise NotImplementedError


# ============================================================================
# STRATEGIC PLANNING PATTERNS
# ============================================================================


class BaronContestDetector(PatternDetector):
    """
    Detect Baron attempts where gold differential makes decision interesting.

    Good for strategic planning because:
    - Multiple options (start, contest, give up)
    - Risk vs reward trade-off
    - Requires considering gold state, vision, numbers
    """

    def __init__(self):
        super().__init__("baron_contest", "strategic_planning")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        events = compressed_match.get("strategic_events", [])
        phase_summaries = compressed_match.get("phase_summaries", {})

        # Find Baron kills
        baron_events = [
            e
            for e in events
            if e.get("type") == "ELITE_MONSTER_KILL"
            and e.get("monster_type") == "BARON_NASHOR"
        ]

        for baron_event in baron_events:
            timestamp = baron_event.get("timestamp_min", 0)
            team = "Blue" if baron_event.get("killer_team_id") == 100 else "Red"

            # Determine game phase
            if timestamp < 14:
                phase = "early"
            elif timestamp < 25:
                phase = "mid"
            else:
                phase = "late"

            # Get gold state at that phase
            phase_summary = phase_summaries.get(phase, {})
            gold_state = phase_summary.get("gold_state", {})
            gold_diff = gold_state.get("difference", 0)

            # Pattern: Close gold makes decision interesting
            # Skip if massive lead/deficit (decision is obvious)
            if abs(gold_diff) < 8000:  # Within 8k gold = interesting
                opportunities.append(
                    {
                        "pattern_type": "baron_contest",
                        "timestamp": timestamp,
                        "team": team,
                        "phase": phase,
                        "gold_diff": gold_diff,
                        "gold_state": gold_state,
                        "event": baron_event,
                    }
                )

        return opportunities


class ObjectiveTradeDetector(PatternDetector):
    """
    Detect scenarios where teams traded objectives (dragon for tower, etc).

    Good for strategic planning because:
    - Evaluating trade value
    - Opportunity cost reasoning
    - Multiple strategic factors
    """

    def __init__(self):
        super().__init__("objective_trade", "strategic_planning")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        events = compressed_match.get("strategic_events", [])

        # Group events by time windows (2 minute windows)
        time_windows = {}
        for event in events:
            timestamp = event.get("timestamp_min", 0)
            window = int(timestamp // 2) * 2  # Round down to nearest 2 minutes

            if window not in time_windows:
                time_windows[window] = []
            time_windows[window].append(event)

        # Find windows where both teams got significant objectives
        for window, window_events in time_windows.items():
            blue_objectives = []
            red_objectives = []

            for event in window_events:
                event_type = event.get("type")

                if event_type == "ELITE_MONSTER_KILL":
                    team = "Blue" if event.get("killer_team_id") == 100 else "Red"
                    obj_type = event.get("monster_type", "objective")

                    if team == "Blue":
                        blue_objectives.append(obj_type)
                    else:
                        red_objectives.append(obj_type)

                elif event_type == "BUILDING_KILL":
                    team_destroyed = "Blue" if event.get("team_id") == 100 else "Red"
                    team_attacker = "Red" if team_destroyed == "Blue" else "Blue"
                    building_type = event.get("building_type", "structure")

                    if team_attacker == "Blue":
                        blue_objectives.append(building_type)
                    else:
                        red_objectives.append(building_type)

            # Pattern: Both teams got something significant = trade scenario
            if blue_objectives and red_objectives:
                opportunities.append(
                    {
                        "pattern_type": "objective_trade",
                        "timestamp": window,
                        "phase": "mid" if window < 25 else "late",
                        "blue_gained": blue_objectives,
                        "red_gained": red_objectives,
                        "events": window_events,
                    }
                )

        return opportunities


# ============================================================================
# CAUSAL INFERENCE PATTERNS
# ============================================================================


class GoldSwingDetector(PatternDetector):
    """
    Detect large gold swings between phases.

    Good for causal inference because:
    - Clear cause-effect relationship to explain
    - Requires tracing causal chains
    - Tests understanding of snowball effects
    """

    def __init__(self, threshold: int = 3000):
        super().__init__("gold_swing", "causal_inference")
        self.threshold = threshold

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        phase_summaries = compressed_match.get("phase_summaries", {})
        phases = ["early", "mid", "late"]

        # Check consecutive phase transitions
        for i in range(len(phases) - 1):
            phase1 = phases[i]
            phase2 = phases[i + 1]

            if phase1 not in phase_summaries or phase2 not in phase_summaries:
                continue

            summary1 = phase_summaries[phase1]
            summary2 = phase_summaries[phase2]

            gold1 = summary1.get("gold_state", {})
            gold2 = summary2.get("gold_state", {})

            diff1 = gold1.get("difference", 0)
            diff2 = gold2.get("difference", 0)

            swing = abs(diff2 - diff1)

            # Pattern: Large swing = something major happened
            if swing >= self.threshold:
                opportunities.append(
                    {
                        "pattern_type": "gold_swing",
                        "phase_start": phase1,
                        "phase_end": phase2,
                        "gold_diff_start": diff1,
                        "gold_diff_end": diff2,
                        "swing_amount": swing,
                        "swing_direction": (
                            "blue_comeback" if diff2 > diff1 else "red_comeback"
                        ),
                    }
                )

        return opportunities


class SnowballEffectDetector(PatternDetector):
    """
    Detect snowball effects - small early lead becoming massive mid/late lead.

    Good for causal inference because:
    - Tests understanding of advantage compounding
    - Multi-step causal chain
    - Common pattern in competitive play
    """

    def __init__(self):
        super().__init__("snowball_effect", "causal_inference")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        phase_summaries = compressed_match.get("phase_summaries", {})

        early = phase_summaries.get("early", {})
        mid = phase_summaries.get("mid", {})
        late = phase_summaries.get("late", {})

        if not early or not mid:
            return []

        early_gold = early.get("gold_state", {})
        mid_gold = mid.get("gold_state", {})

        early_diff = early_gold.get("difference", 0)
        mid_diff = mid_gold.get("difference", 0)

        # Pattern 1: Blue small lead early → big lead mid
        if 1000 <= early_diff <= 3000 and mid_diff >= 6000:
            amplification = mid_diff - early_diff

            opportunities.append(
                {
                    "pattern_type": "snowball_effect",
                    "team": "Blue",
                    "early_lead": early_diff,
                    "mid_lead": mid_diff,
                    "amplification": amplification,
                    "phase_start": "early",
                    "phase_end": "mid",
                }
            )

        # Pattern 2: Red small lead early → big lead mid
        elif -3000 <= early_diff <= -1000 and mid_diff <= -6000:
            amplification = abs(mid_diff) - abs(early_diff)

            opportunities.append(
                {
                    "pattern_type": "snowball_effect",
                    "team": "Red",
                    "early_lead": abs(early_diff),
                    "mid_lead": abs(mid_diff),
                    "amplification": amplification,
                    "phase_start": "early",
                    "phase_end": "mid",
                }
            )

        # Pattern 3: Check mid → late snowball if available
        if late:
            late_gold = late.get("gold_state", {})
            late_diff = late_gold.get("difference", 0)

            # Blue mid lead → massive late lead
            if 2000 <= mid_diff <= 5000 and late_diff >= 10000:
                amplification = late_diff - mid_diff

                opportunities.append(
                    {
                        "pattern_type": "snowball_effect",
                        "team": "Blue",
                        "early_lead": mid_diff,
                        "mid_lead": late_diff,
                        "amplification": amplification,
                        "phase_start": "mid",
                        "phase_end": "late",
                    }
                )

            # Red mid lead → massive late lead
            elif -5000 <= mid_diff <= -2000 and late_diff <= -10000:
                amplification = abs(late_diff) - abs(mid_diff)

                opportunities.append(
                    {
                        "pattern_type": "snowball_effect",
                        "team": "Red",
                        "early_lead": abs(mid_diff),
                        "mid_lead": abs(late_diff),
                        "amplification": amplification,
                        "phase_start": "mid",
                        "phase_end": "late",
                    }
                )

        # Return the most dramatic snowball (highest amplification)
        if opportunities:
            opportunities.sort(key=lambda x: x["amplification"], reverse=True)
            return opportunities[:1]

        return []


class ComebackMechanicDetector(PatternDetector):
    """
    Detect comeback scenarios - team behind early but recovered mid/late.

    Good for causal inference because:
    - Tests understanding of comeback mechanics
    - Multi-causal (objectives, bounties, power spikes)
    - Clear reversal to explain
    """

    def __init__(self):
        super().__init__("comeback_mechanic", "causal_inference")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        phase_summaries = compressed_match.get("phase_summaries", {})

        early = phase_summaries.get("early", {})
        mid = phase_summaries.get("mid", {})
        late = phase_summaries.get("late", {})

        if not early or not mid:
            return []

        early_gold = early.get("gold_state", {})
        mid_gold = mid.get("gold_state", {})

        early_diff = early_gold.get("difference", 0)
        mid_diff = mid_gold.get("difference", 0)

        # Pattern 1: Blue behind early → even/ahead mid (comeback)
        if early_diff <= -3000 and mid_diff >= -1000:
            recovery = mid_diff - early_diff  # How much they recovered

            if recovery >= 4000:  # Significant comeback
                opportunities.append(
                    {
                        "pattern_type": "comeback_mechanic",
                        "team": "Blue",
                        "initial_deficit": abs(early_diff),
                        "final_state": mid_diff,
                        "recovery_amount": recovery,
                        "phase_start": "early",
                        "phase_end": "mid",
                    }
                )

        # Pattern 2: Red behind early → even/ahead mid (comeback)
        elif early_diff >= 3000 and mid_diff <= 1000:
            recovery = abs(mid_diff - early_diff)

            if recovery >= 4000:
                opportunities.append(
                    {
                        "pattern_type": "comeback_mechanic",
                        "team": "Red",
                        "initial_deficit": abs(early_diff),
                        "final_state": abs(mid_diff),
                        "recovery_amount": recovery,
                        "phase_start": "early",
                        "phase_end": "mid",
                    }
                )

        # Pattern 3: Check mid → late comeback if available
        if late:
            late_gold = late.get("gold_state", {})
            late_diff = late_gold.get("difference", 0)

            # Blue behind mid → even/ahead late
            if mid_diff <= -4000 and late_diff >= -1000:
                recovery = late_diff - mid_diff

                if recovery >= 5000:
                    opportunities.append(
                        {
                            "pattern_type": "comeback_mechanic",
                            "team": "Blue",
                            "initial_deficit": abs(mid_diff),
                            "final_state": late_diff,
                            "recovery_amount": recovery,
                            "phase_start": "mid",
                            "phase_end": "late",
                        }
                    )

            # Red behind mid → even/ahead late
            elif mid_diff >= 4000 and late_diff <= 1000:
                recovery = abs(late_diff - mid_diff)

                if recovery >= 5000:
                    opportunities.append(
                        {
                            "pattern_type": "comeback_mechanic",
                            "team": "Red",
                            "initial_deficit": abs(mid_diff),
                            "final_state": abs(late_diff),
                            "recovery_amount": recovery,
                            "phase_start": "mid",
                            "phase_end": "late",
                        }
                    )

        # Return the most dramatic comeback (highest recovery)
        if opportunities:
            opportunities.sort(key=lambda x: x["recovery_amount"], reverse=True)
            return opportunities[:1]

        return []


# ============================================================================
# ERROR DIAGNOSIS PATTERNS
# ============================================================================


class BadBaronAttemptDetector(PatternDetector):
    """
    Detect Baron attempts when team was at severe disadvantage.

    Good for error diagnosis because:
    - Clear strategic mistake
    - Can explain why it was bad
    - Can propose better alternative
    """

    def __init__(self):
        super().__init__("bad_baron_attempt", "error_diagnosis")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        events = compressed_match.get("strategic_events", [])
        phase_summaries = compressed_match.get("phase_summaries", {})

        # Find Baron kills
        baron_events = [
            e
            for e in events
            if e.get("type") == "ELITE_MONSTER_KILL"
            and e.get("monster_type") == "BARON_NASHOR"
        ]

        for baron_event in baron_events:
            timestamp = baron_event.get("timestamp_min", 0)
            team = "Blue" if baron_event.get("killer_team_id") == 100 else "Red"

            # Determine phase
            if timestamp < 14:
                phase = "early"
            elif timestamp < 25:
                phase = "mid"
            else:
                phase = "late"

            # Get gold state
            phase_summary = phase_summaries.get(phase, {})
            gold_state = phase_summary.get("gold_state", {})
            gold_diff = gold_state.get("difference", 0)

            # Adjust for team perspective
            if team == "Red":
                gold_diff = -gold_diff

            # Pattern: Started Baron while at severe disadvantage
            # This is almost always a mistake
            if gold_diff < -5000:  # Team is 5k+ behind
                opportunities.append(
                    {
                        "pattern_type": "bad_baron_attempt",
                        "timestamp": timestamp,
                        "team": team,
                        "phase": phase,
                        "gold_deficit": abs(gold_diff),
                        "gold_state": gold_state,
                    }
                )

        return opportunities


# ============================================================================
# EARLY GAME PATTERNS
# ============================================================================
class FirstDrakeContestDetector(PatternDetector):
    """
    Detect first dragon contest in early game.

    Good for strategic planning because:
    - Early objective control decisions
    - Risk assessment with limited vision
    - Trade-off between drake and other objectives
    """

    def __init__(self):
        super().__init__("first_drake_contest", "strategic_planning")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        events = compressed_match.get("strategic_events", [])
        phase_summaries = compressed_match.get("phase_summaries", {})

        # Find first dragon
        dragons = [
            e
            for e in events
            if e.get("type") == "ELITE_MONSTER_KILL"
            and "DRAGON" in e.get("monster_type", "")
        ]

        if not dragons:
            return []

        first_drake = dragons[0]
        timestamp = first_drake.get("timestamp_min", 0)

        # Only early game drakes (before 14 min)
        if timestamp >= 14:
            return []

        team = "Blue" if first_drake.get("killer_team_id") == 100 else "Red"
        drake_type = first_drake.get("monster_subtype", "Dragon")

        # Get gold state
        early_summary = phase_summaries.get("early", {})
        gold_state = early_summary.get("gold_state", {})
        gold_diff = gold_state.get("difference", 0)

        opportunities.append(
            {
                "pattern_type": "first_drake_contest",
                "timestamp": timestamp,
                "team": team,
                "drake_type": drake_type,
                "phase": "early",
                "gold_diff": gold_diff,
                "gold_state": gold_state,
            }
        )

        return opportunities


class EarlyTowerTradeDetector(PatternDetector):
    """
    Detect early tower trades (before mid game).

    Tests early game resource prioritization and map control.
    """

    def __init__(self):
        super().__init__("early_tower_trade", "strategic_planning")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        events = compressed_match.get("strategic_events", [])

        # Find tower kills in early game
        early_towers = [
            e
            for e in events
            if e.get("type") == "BUILDING_KILL"
            and "TURRET" in e.get("building_type", "")
            and e.get("timestamp_min", 0) < 14  # Early game
        ]

        if len(early_towers) < 2:  # Need at least 2 for a trade
            return []

        # Group by time windows (3 minute windows for early game)
        time_windows = {}
        for tower in early_towers:
            timestamp = tower.get("timestamp_min", 0)
            window = int(timestamp // 3) * 3

            if window not in time_windows:
                time_windows[window] = {"blue": [], "red": []}

            team_destroyed = "Blue" if tower.get("team_id") == 100 else "Red"
            team_attacker = "Red" if team_destroyed == "Blue" else "Blue"

            time_windows[window][team_attacker.lower()].append(tower)

        # Find windows with both teams getting towers
        for window, towers in time_windows.items():
            if towers["blue"] and towers["red"]:
                opportunities.append(
                    {
                        "pattern_type": "early_tower_trade",
                        "timestamp": window,
                        "phase": "early",
                        "blue_towers": len(towers["blue"]),
                        "red_towers": len(towers["red"]),
                        "blue_lanes": [
                            t.get("lane", "UNKNOWN") for t in towers["blue"]
                        ],
                        "red_lanes": [t.get("lane", "UNKNOWN") for t in towers["red"]],
                    }
                )

        return opportunities


# ============================================================================
# SPATIAL REASONING PATTERNS
# ============================================================================


class SplitPushDetector(PatternDetector):
    """
    Detect split push scenarios (lane pressure vs. objective trades).

    Good for spatial reasoning because:
    - Tests understanding of map positioning
    - Multiple simultaneous threats
    - Rotation decision making
    """

    def __init__(self):
        super().__init__("split_push", "spatial_reasoning")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        events = compressed_match.get("strategic_events", [])

        # Look for scenarios where structures fall in multiple lanes simultaneously
        # Group events by 1-minute windows
        time_windows = {}
        for event in events:
            timestamp = event.get("timestamp_min", 0)
            window = int(timestamp)  # 1-minute windows

            if window not in time_windows:
                time_windows[window] = []
            time_windows[window].append(event)

        # Find windows with structures in 2+ different lanes
        for window, window_events in time_windows.items():
            buildings = [e for e in window_events if e.get("type") == "BUILDING_KILL"]

            if len(buildings) < 2:
                continue

            # Check if buildings are in different lanes
            lanes = set(b.get("lane", "NONE") for b in buildings)
            lanes.discard("NONE")  # Remove inhibitors/nexus towers

            if len(lanes) >= 2:  # Multiple lanes = potential split push
                # Determine which team is pushing multiple lanes
                blue_buildings = [
                    b for b in buildings if b.get("team_id") == 200
                ]  # Blue destroys red buildings
                red_buildings = [b for b in buildings if b.get("team_id") == 100]

                if blue_buildings or red_buildings:
                    opportunities.append(
                        {
                            "pattern_type": "split_push",
                            "timestamp": window,
                            "phase": "mid" if window < 25 else "late",
                            "lanes_pressured": list(lanes),
                            "num_lanes": len(lanes),
                            "blue_structures": len(blue_buildings),
                            "red_structures": len(red_buildings),
                        }
                    )

        return opportunities


class MapControlDisparityDetector(PatternDetector):
    """
    Detect scenarios with clear map control imbalance (towers in all 3 lanes).

    Tests spatial reasoning about map control and macro positioning.
    """

    def __init__(self):
        super().__init__("map_control_disparity", "spatial_reasoning")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        events = compressed_match.get("strategic_events", [])

        # Track tower destruction by team and lane over time
        tower_events = [
            e
            for e in events
            if e.get("type") == "BUILDING_KILL"
            and "TURRET" in e.get("building_type", "")
        ]

        # Look for patterns where one team has destroyed towers in all 3 lanes
        # but game is still ongoing (mid-late game)

        blue_destroyed_lanes = set()  # Lanes where blue destroyed towers
        red_destroyed_lanes = set()

        for i, tower in enumerate(tower_events):
            lane = tower.get("lane", "NONE")
            if lane == "NONE":
                continue

            team_destroyed = tower.get("team_id")
            timestamp = tower.get("timestamp_min", 0)

            if team_destroyed == 200:  # Blue destroyed red tower
                blue_destroyed_lanes.add(lane)
            else:  # Red destroyed blue tower
                red_destroyed_lanes.add(lane)

            # Check if one team has all 3 lanes
            if len(blue_destroyed_lanes) == 3 and timestamp >= 14:  # Not too early
                opportunities.append(
                    {
                        "pattern_type": "map_control_disparity",
                        "timestamp": timestamp,
                        "phase": "mid" if timestamp < 25 else "late",
                        "controlling_team": "Blue",
                        "lanes_controlled": list(blue_destroyed_lanes),
                    }
                )
                break  # Only detect once per match

            if len(red_destroyed_lanes) == 3 and timestamp >= 14:
                opportunities.append(
                    {
                        "pattern_type": "map_control_disparity",
                        "timestamp": timestamp,
                        "phase": "mid" if timestamp < 25 else "late",
                        "controlling_team": "Red",
                        "lanes_controlled": list(red_destroyed_lanes),
                    }
                )
                break

        return opportunities


# ============================================================================
# RESOURCE LOGIC PATTERNS
# ============================================================================


class PowerSpikeTimingDetector(PatternDetector):
    """
    Detect power spike moments based on gold thresholds and objectives.

    Good for resource logic because:
    - Tests understanding of gold/item power spikes
    - Timing windows for fights/objectives
    - Resource accumulation vs. immediate action
    """

    def __init__(self):
        super().__init__("power_spike_timing", "resource_logic")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        phase_summaries = compressed_match.get("phase_summaries", {})
        events = compressed_match.get("strategic_events", [])

        # Detect power spikes when team hits gold thresholds
        # Common item breakpoints: ~10k, ~20k, ~30k total team gold

        for phase_name, summary in phase_summaries.items():
            gold_state = summary.get("gold_state", {})
            blue_gold = gold_state.get("blue_total", 0)
            red_gold = gold_state.get("red_total", 0)

            # Look for moments where one team hits power spike threshold
            # while ahead or coming online
            power_spike_thresholds = [
                35000,
                50000,
                65000,
            ]  # 1-item, 2-item, 3-item spikes

            for threshold in power_spike_thresholds:
                # Check if either team just passed threshold
                if blue_gold >= threshold and blue_gold < threshold + 10000:
                    # Blue might have power spike
                    gold_diff = gold_state.get("difference", 0)

                    # Only interesting if game is competitive or they're behind
                    if abs(gold_diff) < 8000 or gold_diff < 0:
                        opportunities.append(
                            {
                                "pattern_type": "power_spike_timing",
                                "timestamp": None,  # Phase-based
                                "phase": phase_name,
                                "team": "Blue",
                                "team_gold": blue_gold,
                                "gold_diff": gold_diff,
                                "spike_type": f"{threshold//1000}k_spike",
                            }
                        )

                if red_gold >= threshold and red_gold < threshold + 10000:
                    gold_diff = gold_state.get("difference", 0)

                    if (
                        abs(gold_diff) < 8000 or gold_diff > 0
                    ):  # Red behind = negative diff
                        opportunities.append(
                            {
                                "pattern_type": "power_spike_timing",
                                "timestamp": None,
                                "phase": phase_name,
                                "team": "Red",
                                "team_gold": red_gold,
                                "gold_diff": gold_diff,
                                "spike_type": f"{threshold//1000}k_spike",
                            }
                        )

        # Limit to 1-2 most interesting per match
        return opportunities[:2]


class ScalingDecisionDetector(PatternDetector):
    """
    Detect scenarios where team must decide between fighting now vs. scaling.

    Tests resource logic about gold accumulation, comp scaling, and timing.
    """

    def __init__(self):
        super().__init__("scaling_decision", "resource_logic")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        phase_summaries = compressed_match.get("phase_summaries", {})

        # Look for scenarios where a team is behind early/mid but game continues
        # This suggests they're trying to scale

        early = phase_summaries.get("early", {})
        mid = phase_summaries.get("mid", {})

        if not early or not mid:
            return []

        early_gold = early.get("gold_state", {})
        mid_gold = mid.get("gold_state", {})

        early_diff = early_gold.get("difference", 0)
        mid_diff = mid_gold.get("difference", 0)

        # Pattern: Team behind early, still behind mid, but differential narrowing
        # = They're successfully scaling

        if early_diff < -2000 and mid_diff < 0:  # Blue behind in early, still behind
            swing = abs(mid_diff - early_diff)

            if swing < 3000:  # Deficit not growing much = successful stall
                opportunities.append(
                    {
                        "pattern_type": "scaling_decision",
                        "timestamp": 14,  # Early-to-mid transition
                        "phase": "mid",
                        "team": "Blue",
                        "early_deficit": abs(early_diff),
                        "mid_deficit": abs(mid_diff),
                        "scaling_success": swing < 1000,  # Narrowing gap
                    }
                )

        elif early_diff > 2000 and mid_diff > 0:  # Red behind
            swing = abs(mid_diff - early_diff)

            if swing < 3000:
                opportunities.append(
                    {
                        "pattern_type": "scaling_decision",
                        "timestamp": 14,
                        "phase": "mid",
                        "team": "Red",
                        "early_deficit": abs(early_diff),
                        "mid_deficit": abs(mid_diff),
                        "scaling_success": swing < 1000,
                    }
                )

        return opportunities


# ============================================================================
# ERROR DIAGNOSIS PATTERNS (Additional)
# ============================================================================


class BadTeamfightDetector(PatternDetector):
    """
    Detect teamfights that one team clearly should have avoided.

    Good for error diagnosis because:
    - Clear strategic mistake (fighting at disadvantage)
    - Can identify what went wrong
    - Can propose better alternative
    """

    def __init__(self):
        super().__init__("bad_teamfight", "error_diagnosis")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        phase_summaries = compressed_match.get("phase_summaries", {})
        events = compressed_match.get("strategic_events", [])

        # Look for phases where gold swung heavily against one team
        # This often indicates a bad fight

        for phase_name, summary in phase_summaries.items():
            gold_state = summary.get("gold_state", {})
            swing = gold_state.get("swing", 0)
            gold_diff_end = gold_state.get("difference", 0)

            # Pattern: Team lost significant gold (swing > 5k)
            # and ended phase at disadvantage
            # This suggests they took a bad fight

            if abs(swing) >= 5000:  # Significant swing
                # Determine which team lost the fight
                if swing < -5000:  # Blue lost ground badly
                    if gold_diff_end < -3000:  # And ended behind
                        opportunities.append(
                            {
                                "pattern_type": "bad_teamfight",
                                "phase": phase_name,
                                "team": "Blue",
                                "gold_swing": swing,
                                "resulting_deficit": abs(gold_diff_end),
                                "timestamp": None,  # Phase-based
                            }
                        )

                elif swing > 5000:  # Red lost ground badly
                    if (
                        gold_diff_end > 3000
                    ):  # And ended behind (from Red's perspective)
                        opportunities.append(
                            {
                                "pattern_type": "bad_teamfight",
                                "phase": phase_name,
                                "team": "Red",
                                "gold_swing": abs(swing),
                                "resulting_deficit": abs(gold_diff_end),
                                "timestamp": None,
                            }
                        )

        # Limit to 1 per match (the worst one)
        return opportunities[:1]


class OverextensionDetector(PatternDetector):
    """
    Detect scenarios where team lost structures while pushing deep.

    Indicates poor map awareness and macro decision-making.
    """

    def __init__(self):
        super().__init__("overextension", "error_diagnosis")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        events = compressed_match.get("strategic_events", [])

        # Find building kills
        buildings = [e for e in events if e.get("type") == "BUILDING_KILL"]

        if not buildings:
            return []

        # Look for pattern: Team destroyed enemy structure in one lane,
        # but lost their own structure in a different lane around same time
        # This suggests overextension

        # Group by time windows (2 minute windows)
        time_windows = {}
        for building in buildings:
            timestamp = building.get("timestamp_min", 0)
            window = int(timestamp // 2) * 2

            if window not in time_windows:
                time_windows[window] = {"blue_destroyed": [], "red_destroyed": []}

            team_destroyed = building.get("team_id")
            lane = building.get("lane", "NONE")
            building_type = building.get("building_type", "UNKNOWN")

            # Check if it's a significant structure (not just outer tower)
            is_significant = (
                "INNER" in building_type
                or "INHIBITOR" in building_type
                or "BASE" in building_type
            )

            if team_destroyed == 200:  # Blue's structure destroyed
                time_windows[window]["blue_destroyed"].append(
                    {"lane": lane, "type": building_type, "significant": is_significant}
                )
            else:  # Red's structure destroyed
                time_windows[window]["red_destroyed"].append(
                    {"lane": lane, "type": building_type, "significant": is_significant}
                )

        # Find windows where one team traded unfavorably
        # (lost significant structure while taking less important one)
        for window, structures in time_windows.items():
            blue_destroyed = structures["blue_destroyed"]
            red_destroyed = structures["red_destroyed"]

            # Blue overextended: Blue took enemy tower but lost inhibitor/base tower
            blue_lost_significant = any(s["significant"] for s in blue_destroyed)
            red_took_minor = red_destroyed and not any(
                s["significant"] for s in red_destroyed
            )

            if blue_lost_significant and red_took_minor and len(blue_destroyed) > 0:
                # Blue overextended
                opportunities.append(
                    {
                        "pattern_type": "overextension",
                        "timestamp": window,
                        "phase": "mid" if window < 25 else "late",
                        "team": "Blue",
                        "lost": [s["type"] for s in blue_destroyed],
                        "gained": (
                            [s["type"] for s in red_destroyed] if red_destroyed else []
                        ),
                    }
                )

            # Red overextended: Red took enemy tower but lost inhibitor/base tower
            red_lost_significant = any(s["significant"] for s in red_destroyed)
            blue_took_minor = blue_destroyed and not any(
                s["significant"] for s in blue_destroyed
            )

            if red_lost_significant and blue_took_minor and len(red_destroyed) > 0:
                opportunities.append(
                    {
                        "pattern_type": "overextension",
                        "timestamp": window,
                        "phase": "mid" if window < 25 else "late",
                        "team": "Red",
                        "lost": [s["type"] for s in red_destroyed],
                        "gained": (
                            [s["type"] for s in blue_destroyed]
                            if blue_destroyed
                            else []
                        ),
                    }
                )

        # Limit to 1-2 most clear cases
        return opportunities[:2]


class MissedObjectiveDetector(PatternDetector):
    """
    Detect scenarios where team could have taken objective but didn't.

    Indicates poor game sense and opportunity recognition.
    """

    def __init__(self):
        super().__init__("missed_objective", "error_diagnosis")

    def detect(self, compressed_match: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities = []

        events = compressed_match.get("strategic_events", [])
        phase_summaries = compressed_match.get("phase_summaries", {})

        # Find objective takes
        objectives = [e for e in events if e.get("type") == "ELITE_MONSTER_KILL"]

        if not objectives:
            return []

        # Look for pattern: Team took objective while having significant advantage
        # Suggests enemy team had opportunity earlier but didn't take it

        for obj in objectives:
            timestamp = obj.get("timestamp_min", 0)
            obj_type = obj.get("monster_type", "")
            team_took = "Blue" if obj.get("killer_team_id") == 100 else "Red"

            # Determine phase
            if timestamp < 14:
                phase = "early"
            elif timestamp < 25:
                phase = "mid"
            else:
                phase = "late"

            # Get gold state
            phase_summary = phase_summaries.get(phase, {})
            gold_state = phase_summary.get("gold_state", {})
            gold_diff = gold_state.get("difference", 0)

            # Adjust for team perspective
            if team_took == "Red":
                gold_diff = -gold_diff

            # Pattern: Team took objective while being significantly behind
            # This suggests the winning team missed the opportunity
            if gold_diff < -4000:  # Team is 4k+ behind but still got objective
                missed_team = "Blue" if team_took == "Red" else "Red"

                # This is a missed opportunity for the winning team
                opportunities.append(
                    {
                        "pattern_type": "missed_objective",
                        "timestamp": timestamp,
                        "phase": phase,
                        "missed_team": missed_team,  # Team that SHOULD have taken it
                        "actual_team": team_took,  # Team that DID take it
                        "objective": obj_type,
                        "gold_advantage": abs(gold_diff),  # How far ahead they were
                    }
                )

        # Only return most egregious cases (biggest gold advantages)
        opportunities.sort(key=lambda x: x["gold_advantage"], reverse=True)
        return opportunities[:1]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_all_detectors() -> List[PatternDetector]:
    """Get all available pattern detectors"""
    return [
        # Strategic Planning
        BaronContestDetector(),
        ObjectiveTradeDetector(),
        FirstDrakeContestDetector(),
        EarlyTowerTradeDetector(),
        # Causal Inference
        # GoldSwingDetector(threshold=3000),
        GoldSwingDetector(threshold=5000),
        SnowballEffectDetector(),
        ComebackMechanicDetector(),
        # Error Diagnosis
        BadBaronAttemptDetector(),
        BadTeamfightDetector(),
        OverextensionDetector(),
        MissedObjectiveDetector(),
        # Spatial Reasoning
        SplitPushDetector(),
        MapControlDisparityDetector(),
        # Resource Logic
        PowerSpikeTimingDetector(),
        ScalingDecisionDetector(),
    ]


def detect_all_patterns(
    compressed_match: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run all pattern detectors on a match.

    Returns:
        Dict mapping pattern type to list of opportunities
    """
    detectors = get_all_detectors()
    all_opportunities = {}

    for detector in detectors:
        opportunities = detector.detect(compressed_match)

        if opportunities:
            pattern_name = detector.name
            if pattern_name not in all_opportunities:
                all_opportunities[pattern_name] = []
            all_opportunities[pattern_name].extend(opportunities)

    return all_opportunities
