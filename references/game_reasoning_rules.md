# Game-Domain Reasoning Rules for League of Legends

**Version:** 1.0  
**Last Updated:** February 2026  
**Purpose:** Define deterministic rules that become ground truth constraints in benchmark evaluation

---

## Overview

This document codifies strategic principles from League of Legends into **deterministic rules** that can be programmatically checked. These rules form the **rule-based component** of the hybrid evaluation framework.

**Key Principle:** While League of Legends is a complex game with many contextual factors, certain strategic principles are **universally valid** and violations indicate flawed reasoning.

---

## 1. Baron Nashor Rules

### Rule 1.1: Never Start Baron When Severely Behind

**Constraint:** Do NOT recommend starting Baron when team is **8,000+ gold behind**

**Rationale:**
- Baron has high DPS and requires time to kill
- Being far behind means losing teamfights if contested
- Risk of enemy steal + wipe is game-ending
- Even if successful, Baron buff doesn't close 8k+ gold gap

**Exceptions:** None. This is absolute.

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="baron_severe_deficit",
    constraint_type="must_not_recommend",
    parameters={
        "forbidden_phrases": [
            "start baron",
            "take baron",
            "do baron"
        ],
        "context_condition": "gold_diff < -8000"
    }
)
```

### Rule 1.2: Vision Control Required for Baron

**Constraint:** Must mention vision/control when discussing Baron attempts

**Rationale:**
- Baron steals are high-impact game turners
- Vision control determines contest safety
- Smite timing requires line of sight

**Keywords that satisfy:** vision, sight, ward, control, see, clear

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="baron_vision_requirement",
    constraint_type="must_mention",
    parameters={
        "keywords": ["vision", "sight", "ward", "control", "see", "clear"],
        "min_mentions": 1,
        "context": "when discussing baron attempt"
    }
)
```

### Rule 1.3: Never Start Baron When Outnumbered

**Constraint:** Do NOT recommend starting Baron when fighting 4v5 or worse

**Rationale:**
- Enemy team can force fight during Baron
- Numerical disadvantage = lost teamfight
- Baron + teamfight loss = game over

**Exceptions:** 
- If missing player is enemy (5v4 in your favor) - Baron is good
- If enemies are all on opposite side of map with no TP

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="baron_numerical_disadvantage",
    constraint_type="must_not_recommend",
    parameters={
        "forbidden_action": "start_baron",
        "condition": "alive_teammates <= alive_enemies - 1"
    }
)
```

---

## 2. Teamfight Engagement Rules

### Rule 2.1: Never Engage When Numbers Disadvantaged

**Constraint:** Do NOT recommend forcing fight when down 2+ members

**Rationale:**
- 5v3 is mathematically unwinnable unless massive gold lead (15k+)
- Even 5v4 is very difficult
- Better to disengage, give objective, prevent wipe

**Exceptions:**
- If defending Nexus (must fight regardless)
- If enemy is at <20% HP (cleanup, not engage)

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="fight_numerical_disadvantage",
    constraint_type="must_not_recommend",
    parameters={
        "forbidden_action": "engage teamfight",
        "condition": "alive_teammates < alive_enemies - 1",
        "exception": "defending_nexus == True"
    }
)
```

### Rule 2.2: Consider Ultimate Availability

**Constraint:** Must mention ultimate availability for teamfight decisions

**Rationale:**
- Ultimates define teamfight outcomes
- Fighting without key ults (Malphite, Amumu, etc.) is usually bad
- Enemy having ults when you don't is major disadvantage

**Keywords that satisfy:** ultimate, ult, R, ability, cooldown

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="teamfight_ultimate_consideration",
    constraint_type="must_mention",
    parameters={
        "keywords": ["ultimate", "ult", "R", "ability", "cooldown"],
        "min_mentions": 1,
        "context": "when recommending teamfight engage"
    }
)
```

---

## 3. Objective Priority Rules

### Rule 3.1: Early Game Objective Hierarchy

**Time Range:** 0-14 minutes

**Priority Order (General):**
1. First Tower Gold (400g total) + Plates (160g each)
2. Rift Herald (charges to break towers)
3. Dragon (permanent buff but less immediate impact)

**Exception:** Dragon Soul Setup
- If dragon is 3rd for team (soul point at 4th), priority increases
- Infernal/Ocean dragons may justify higher priority

**Constraint:** When comparing early game objectives, must acknowledge tower/herald value

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="early_game_objective_priority",
    constraint_type="logical_consistency",
    parameters={
        "if_timestamp": "< 14 minutes",
        "then_acknowledge": ["first tower", "herald", "plates"],
        "context": "when ranking objective priority"
    }
)
```

### Rule 3.2: Mid Game - Dragon Soul Priority

**Time Range:** 14-25 minutes

**Rule:** Soul point dragon (3rd or 4th) > Baron > Other objectives

**Rationale:**
- Dragon soul is game-changing permanent buff
- More valuable than gold from towers
- Worth fighting teamfights for

**Constraint:** When soul point dragon is available, must identify it as high priority

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="soul_point_priority",
    constraint_type="must_mention",
    parameters={
        "if_condition": "dragon_count >= 2",  # 3rd or 4th dragon
        "then_must_include": ["soul", "high priority", "priority"],
        "context": "when discussing dragon contest"
    }
)
```

### Rule 3.3: Late Game - Elder Dragon Absolute Priority

**Time Range:** 25+ minutes (when Elder spawns)

**Rule:** Elder Dragon > Everything else (except Nexus defense)

**Rationale:**
- Elder execute effect on low HP enemies
- Effectively wins teamfights
- With Elder + Baron, game is essentially won

**Constraint:** Must acknowledge Elder as highest priority objective

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="elder_dragon_priority",
    constraint_type="must_acknowledge",
    parameters={
        "if_condition": "elder_dragon_available == True",
        "then_statement": "elder is highest priority",
        "or_keywords": ["elder", "priority", "must contest"]
    }
)
```

---

## 4. Gold Economy Rules

### Rule 4.1: Tower > Kills (Usually)

**Rule:** Trading 2-3 kills for a tower is usually worth

**Rationale:**
- Tower: 150g global + 250g (first tower) + plates = 400-800g total
- Kills: 300g each = 600-900g for 2-3 kills
- Tower also gives map control

**Constraint:** When evaluating kill vs. tower trade, must consider tower gold

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="tower_gold_value",
    constraint_type="numeric_awareness",
    parameters={
        "if_comparing": ["kills", "tower"],
        "must_acknowledge": "tower gold value ~400-800g",
        "or_mention": ["tower gold", "global gold", "first tower bonus"]
    }
)
```

### Rule 4.2: Baron Buff Value

**Rule:** Baron buff is worth approximately 1,500 gold in combat stats

**Rationale:**
- 40 AD/AP + other stats
- Empowered recall
- Minion buffs for sieging
- Effectively gives gold lead even if gold is even

**Constraint:** When discussing Baron value, acknowledge it's worth 1000-2000g in stats

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="baron_gold_equivalent",
    constraint_type="numeric_awareness",
    parameters={
        "if_discussing": "baron value",
        "acceptable_range": "1000-2000 gold equivalent",
        "or_keywords": ["stats", "buff value", "gold worth"]
    }
)
```

### Rule 4.3: Dragon Soul > Gold Lead

**Rule:** Dragon soul is worth more than a 3,000-5,000 gold lead

**Rationale:**
- Permanent buff that affects all teamfights
- Cannot be countered by items
- Often decides late game outcomes

**Constraint:** When comparing dragon soul to gold, soul should be valued highly

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="soul_vs_gold",
    constraint_type="comparative_value",
    parameters={
        "if_comparing": ["dragon soul", "gold lead"],
        "then": "soul > 3000 gold lead",
        "keywords": ["soul", "permanent", "game changing"]
    }
)
```

---

## 5. Vision Control Rules

### Rule 5.1: Face-Checking is High Risk

**Rule:** Do NOT recommend face-checking unwarded areas without vision

**Rationale:**
- Face-checking = walking into fog of war
- High risk of being caught and killed
- Gives free kill + objective to enemy

**Exceptions:**
- If target is confirmed low HP and alone
- If you have escape tool (Flash, dash) and expect danger

**Constraint:** When suggesting entering fog of war, must acknowledge risk

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="facecheck_risk_acknowledgment",
    constraint_type="must_mention",
    parameters={
        "if_action": "entering unwarded area",
        "then_must_mention": ["risk", "danger", "vision", "check"],
        "or_suggest": ["ward first", "use ability to check"]
    }
)
```

### Rule 5.2: Vision Required for Objective Control

**Rule:** Must establish vision before taking major objectives (Baron, Elder)

**Rationale:**
- Without vision, enemy can sneak in and steal
- Stolen Baron/Elder often loses game
- Vision control = safe objective taking

**Constraint:** Objective recommendations must mention vision setup

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="objective_vision_setup",
    constraint_type="must_mention",
    parameters={
        "if_recommending": ["baron", "elder"],
        "must_include": ["vision", "ward", "clear", "control"],
        "min_mentions": 1
    }
)
```

---

## 6. Spatial Positioning Rules

### Rule 6.1: Split Push Requires Number Advantage Elsewhere

**Rule:** Split pushing is only effective if the 4-person group can hold or threaten

**Rationale:**
- If 4v5 gets engaged on and loses, split pusher can't save them
- Split push creates map pressure ONLY if other team must respond
- If enemies ignore split and win 5v4, split push fails

**Constraint:** Split push recommendations must address the 4v5 elsewhere

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="split_push_number_consideration",
    constraint_type="must_address",
    parameters={
        "if_recommending": "split push",
        "must_discuss": ["4v5", "rest of team", "hold", "disengage"],
        "min_mentions": 1
    }
)
```

### Rule 6.2: Rotation Time Matters

**Rule:** Must account for travel time when discussing rotations

**Rationale:**
- Dragon spawns in 30 seconds, but top laner is 45 seconds away = can't make it
- Objectives can be taken before rotation completes
- Overestimating rotation speed = bad calls

**Constraint:** Rotation recommendations must acknowledge timing/distance

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="rotation_timing_awareness",
    constraint_type="must_mention",
    parameters={
        "if_discussing": "rotation",
        "must_acknowledge": ["time", "seconds", "distance", "arrive"],
        "or_calculate": "travel time estimate"
    }
)
```

---

## 7. Power Spike Rules

### Rule 7.1: Level 6 Power Spike

**Rule:** Level 6 is a major power spike (unlocks ultimate)

**Rationale:**
- Champions with strong ult (Malphite, Syndra, Zed) spike hard at 6
- 6v5 in levels often determines all-in outcomes
- Ignoring level disadvantage = deaths

**Constraint:** When discussing early all-ins, must mention level advantage

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="level_6_spike_awareness",
    constraint_type="must_mention",
    parameters={
        "if_context": "early game all-in (< 10 minutes)",
        "must_consider": ["level", "level 6", "ultimate", "ult advantage"],
        "min_mentions": 1
    }
)
```

### Rule 7.2: Item Spike Windows

**Rule:** Major item completions (1st item, 2-item, 3-item) create power spikes

**Rationale:**
- Completing Infinity Edge vs. components = huge damage spike
- Finished items > components of next item
- Power spike timing determines when to fight

**Constraint:** When discussing teamfight timing, may mention item spikes

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="item_spike_consideration",
    constraint_type="optional_mention",
    parameters={
        "if_context": "should we fight now",
        "good_to_mention": ["items", "item spike", "completed", "power spike"],
        "importance": "expected" # not required, but good reasoning includes it
    }
)
```

---

## 8. Causal Chain Rules

### Rule 8.1: Gold Swings Have Causes

**Rule:** Large gold swings (3,000+) don't happen randomly - there's always a cause

**Rationale:**
- Teamfight ace = 1500g + towers/objectives
- Lost Baron = 1500g buff swing
- Every major swing has identifiable cause

**Constraint:** When explaining gold swing, must identify specific events

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="gold_swing_causation",
    constraint_type="must_identify",
    parameters={
        "if_context": "gold swing > 3000",
        "must_identify": "specific event (teamfight, baron, towers)",
        "cannot_say": "random", "luck", "just happened"
    }
)
```

### Rule 8.2: Snowball Effects

**Rule:** Early advantages cascade if not addressed

**Rationale:**
- Early kill → Gold lead → Item advantage → Win more fights → Larger lead
- Each advantage compounds
- Ignoring this = failing to trace causal chains

**Constraint:** When explaining how small lead became large, mention cascading

**Implementation:**
```python
GroundTruthConstraint(
    constraint_id="snowball_cascade_understanding",
    constraint_type="must_explain",
    parameters={
        "if_context": "small lead became large lead",
        "must_mention": ["cascade", "compound", "snowball", "led to"],
        "or_show": "chain of events A → B → C"
    }
)
```

---

## 9. Common Fallacies to Avoid

### Fallacy 9.1: "We're Ahead in Gold = We Win"

**Error:** Assuming gold lead guarantees victory

**Counter:** Team composition scaling matters more late game

**Constraint:** Cannot recommend forcing late game when comp doesn't scale

### Fallacy 9.2: "Kills > Objectives"

**Error:** Valuing kills over towers/dragons

**Counter:** Towers give global gold + map control, often worth more than kills

**Constraint:** Cannot claim kills are more valuable than objectives without context

### Fallacy 9.3: "We Won Fight = We Should Baron"

**Error:** Auto-assuming Baron after winning teamfight

**Counter:** Must consider: how many alive, HP states, death timers, enemy respawns

**Constraint:** Baron recommendation requires more than "we won fight"

---

## 10. Rule Application Guidelines

### Severity Levels

**Critical Violations (Game-Losing):**
- Recommending Baron when 8k+ behind
- Recommending 3v5 teamfight
- Ignoring Elder Dragon priority

**Major Violations (Significant Error):**
- Not mentioning vision for Baron
- Ignoring numerical advantages
- Face-checking without acknowledging risk

**Minor Violations (Suboptimal but not Game-Losing):**
- Not mentioning item spikes
- Slightly wrong gold value estimates
- Missing secondary considerations

### Enforcement in Evaluation

**Hard Constraints (Must Pass):**
- Critical and Major violations = automatic failure
- These are `must_mention` or `must_not_recommend` constraints

**Soft Constraints (Points Deducted):**
- Minor violations = reduced score but not failure
- These are `expected` or `optional` considerations

---

## 11. Constraint Schema Mapping

Each rule maps to a `GroundTruthConstraint` with these fields:

```python
GroundTruthConstraint(
    constraint_id: str           # Unique identifier
    description: str              # Human-readable explanation
    constraint_type: str          # must_mention, must_not_recommend, numeric_threshold, etc.
    parameters: Dict[str, Any]    # Type-specific parameters
)
```

**Constraint Types:**

1. **must_mention**: Response must contain certain keywords
2. **must_not_recommend**: Response cannot suggest certain actions
3. **numeric_threshold**: Numeric values must be within range
4. **logical_consistency**: If X then Y must be present
5. **must_acknowledge**: Must show awareness of concept
6. **comparative_value**: When comparing A vs B, correct ordering

---

## Version History

**v1.0 (February 2026):**
- Initial rule set covering Baron, teamfights, objectives, economy, vision, positioning, power spikes
- Based on Season 14 meta
- 35+ deterministic rules defined

**Future Updates:**
- Rule refinement based on evaluation results
- Addition of champion-specific rules (if needed)
- Meta-specific adjustments for major patches

---

## Usage in Benchmark

These rules are used in two ways:

1. **Task Generation**: Rules identify what makes a scenario interesting
   - Example: "Find matches where Baron was started with <8k deficit" = potential error diagnosis task

2. **Evaluation**: Rules become automated checks
   - Example: If task asks about Baron and model recommends it despite 10k deficit, constraint violation = failed

**Integration with LLM-as-Judge:**
- Rule-based checks provide objective floor (binary pass/fail)
- LLM-as-judge provides subjective ceiling (reasoning quality 1-5)
- Hybrid = both must pass for high score

---

## Acknowledgments

Rules derived from:
- Competitive LoL analysis (LCS, LCK, Worlds)
- High-elo educational content
- Riot Games official guides
- Professional coaching methodologies

**Important:** These are heuristic rules that hold in >95% of cases. Edge cases exist, but violating these rules without exceptional justification indicates flawed reasoning.