# Reasoning Taxonomy for League of Legends LLM Benchmark

**Version:** 1.0  
**Last Updated:** February 2026  
**Author:** Jared

---

## Overview

This document defines the five reasoning modalities evaluated in the LoL LLM benchmark. Each modality tests distinct cognitive capabilities required for strategic understanding in complex, multi-agent game environments.

The taxonomy is designed to distinguish **surface-level pattern matching** from **genuine strategic reasoning** by evaluating models on their ability to:
- Consider multiple strategic factors simultaneously
- Trace causal chains across game events
- Identify suboptimal decisions and explain why
- Reason about spatial positioning and map control
- Evaluate resource trade-offs and economic principles

---

## 1. Strategic Planning

### Definition
The ability to evaluate multiple forward-looking options and select optimal actions based on current game state, resource availability, and anticipated opponent responses.

### Cognitive Skills Tested
- **Multi-option evaluation**: Weighing pros/cons of different strategic choices
- **Resource state consideration**: Factoring in gold leads, item advantages, cooldown availability
- **Opponent response prediction**: Anticipating how enemies will react to your plays
- **Objective prioritization**: Ranking available objectives by value and risk
- **Contingency planning**: Identifying backup plans if primary strategy fails

### Strategic Depth Levels

**Level 1 (Basic):** Single-factor reasoning
- Example: "Take dragon because it's available"
- Considers only immediate opportunity

**Level 2 (Intermediate):** Multi-factor reasoning
- Example: "Take dragon because it's Infernal (high value), we have number advantage (4v3), and enemy jungler is top side (low contest risk)"
- Considers multiple game state factors

**Level 3 (Advanced):** Strategic chain reasoning
- Example: "Trade dragon for Herald because we can crash top wave, guarantee Herald, take first tower gold (400g + plates), rotate mid for vision control, set up next dragon (soul point) at 20 minutes with item advantage"
- Plans multiple moves ahead with interconnected outcomes

### Example Scenarios

**Objective Contest Decisions:**
- Should we contest this Baron Nashor?
- Is it worth trading dragon for towers?
- When should we force a teamfight vs. split push?

**Macro Rotations:**
- Should we rotate to defend bottom inhibitor or force top?
- Is it better to recall or push for one more wave?

**Team Fight Engagement:**
- Should we engage this fight or disengage and reset?
- Is our team composition stronger in skirmishes or 5v5?

### Evaluation Criteria

A high-quality strategic planning response should:
1. ✅ Identify multiple viable options (not just one)
2. ✅ Consider current game state (gold, items, levels, objectives)
3. ✅ Evaluate risks vs. rewards explicitly
4. ✅ Reference team compositions and power spikes
5. ✅ Suggest contingencies or conditions ("if X happens, do Y")
6. ✅ Avoid absolute statements without caveats

**Red flags:**
- ❌ Ignoring obvious risks
- ❌ Recommending clearly game-losing plays
- ❌ Not considering opponent's perspective
- ❌ Treating all objectives as equally valuable

---

## 2. Causal Inference

### Definition
The ability to trace backward from outcomes to causes, identify critical decision points, and understand how earlier events cascade into later consequences.

### Cognitive Skills Tested
- **Backward reasoning**: Working from result to cause
- **Critical moment identification**: Finding the turning point in a sequence
- **Causal chain tracing**: Understanding X → Y → Z relationships
- **Confounding factor awareness**: Recognizing when correlation ≠ causation
- **Counterfactual thinking**: Understanding what would have happened if decisions were different

### Causal Relationship Types

**Direct Causation:**
- Lost teamfight → Lost Baron → Lost game
- Took first tower → Gold advantage → Item spike → Won next fight

**Indirect Causation:**
- Vision denial → Enemy invaded safely → Got first blood → Snowballed lane

**Cascading Effects:**
- Missed one CS wave → Hit level 6 late → Lost all-in fight → Lost tower → Lost map control

**False Causation (Common Errors):**
- "We won early game → We should win late" (ignores team scaling)
- "We have gold lead → We're winning" (ignores power spike timing)

### Example Scenarios

**Gold Swing Analysis:**
- "Blue team had a 1,400 gold lead early but fell behind by 2,400 mid-game. What caused this 3,800 gold reversal?"

**Teamfight Outcome Explanation:**
- "Red team lost this teamfight despite having a gold advantage. Why?"

**Objective Loss Chain:**
- "How did losing first dragon lead to losing the game 15 minutes later?"

**Snowball Effect Tracing:**
- "Blue's bot lane died once at 4 minutes. By 15 minutes, they were 50 CS behind and lost 3 towers. Explain the causal chain."

### Evaluation Criteria

A high-quality causal inference response should:
1. ✅ Identify the **primary cause** (most impactful event)
2. ✅ Trace the **causal chain** (how A led to B led to C)
3. ✅ Acknowledge **contributing factors** (not just one cause)
4. ✅ Distinguish **correlation from causation**
5. ✅ Reference **specific game events** with timestamps
6. ✅ Explain **why** each step in the chain occurred

**Red flags:**
- ❌ Confusing correlation with causation
- ❌ Ignoring the timeline of events
- ❌ Attributing outcomes to single factors when multiple caused it
- ❌ Not explaining the mechanism (the "why" behind the chain)

---

## 3. Error Diagnosis

### Definition
The ability to identify strategic mistakes, explain why decisions were suboptimal, and propose better alternatives that would have led to more favorable outcomes.

### Cognitive Skills Tested
- **Mistake identification**: Recognizing decisions that deviate from optimal play
- **Explanation of suboptimality**: Articulating why a decision was bad
- **Alternative generation**: Proposing what should have been done instead
- **Severity assessment**: Distinguishing minor errors from game-losing blunders
- **Root cause analysis**: Finding the underlying mistake (not just symptoms)

### Error Categories

**Strategic Errors (Macro):**
- Starting Baron with low HP and no vision
- Fighting when down in gold/levels/numbers
- Not respecting enemy power spikes
- Ignoring objective timers

**Tactical Errors (Micro):**
- Face-checking bushes without vision
- Overextending without escape tools
- Greeding for CS/kills when recall is needed

**Resource Management Errors:**
- Recalling with full mana when dragon is spawning
- Using ultimate on a support when ADC is present
- Wasting Flash when death is inevitable

**Information Errors:**
- Not tracking enemy summoner spells
- Ignoring minimap warnings
- Missing enemy rotations

### Example Scenarios

**Classic Blunders:**
- "Blue started Baron at 6k gold deficit with 3 members. They got aced. What was the mistake?"

**Subtle Errors:**
- "Red used their team's only engage tool (Malphite ult) on the enemy support, then couldn't start the teamfight. What should they have done?"

**Compound Errors:**
- "Blue won a teamfight but recalled instead of taking Baron. Red respawned, won the next fight, and took Baron themselves. Diagnose the error chain."

**Hindsight Analysis:**
- "Looking at how this game ended, what was the critical mistake Blue made at 18 minutes that sealed their loss?"

### Evaluation Criteria

A high-quality error diagnosis response should:
1. ✅ **Identify the specific error** (what was done wrong)
2. ✅ **Explain why it was wrong** (game state context)
3. ✅ **Propose a better alternative** (what should have been done)
4. ✅ **Assess severity** (minor mistake vs. game-losing)
5. ✅ **Consider information availability** (was the right decision possible with available info?)
6. ✅ **Avoid hindsight bias** (not using information players couldn't have known)

**Red flags:**
- ❌ Justifying obviously bad plays
- ❌ Using information players didn't have at the time
- ❌ Not proposing concrete alternatives
- ❌ Treating all errors as equally severe

---

## 4. Spatial Reasoning

### Definition
The ability to reason about map positioning, territorial control, rotation timing, and the geometric relationships between champions, objectives, and structures.

### Cognitive Skills Tested
- **Map geometry understanding**: Knowing distances, paths, and line-of-sight
- **Positioning advantage recognition**: Understanding when position creates leverage
- **Rotation timing calculation**: Estimating travel time and opportunity windows
- **Zone control reasoning**: Understanding which team controls which map areas
- **Split-push threat assessment**: Evaluating when split pressure creates advantages

### Spatial Concepts

**Map Quadrants:**
- Top-side vs. Bot-side control
- Blue jungle vs. Red jungle presence
- Lane priority (which lanes are pushed)

**Numerical Advantages:**
- 5v4 scenarios (one player split pushing or dead)
- 2v1 ganks
- 3v2 skirmishes in jungle

**Rotation Mechanics:**
- TP flanks
- Collapse timing (how fast team can rotate)
- Wave management affecting rotation ability

**Vision Control:**
- Vision denial zones
- Fog of war exploitation
- Ward placement for map awareness

### Example Scenarios

**Split Push Decisions:**
- "Blue has Fiora split pushing top while 4 members pressure mid. Red has all 5 defending mid. What should Red do?"

**Rotation Optimization:**
- "Dragon spawns in 30 seconds. Blue's top laner is pushing bot tier 2 tower. Should they rotate to dragon or continue pushing?"

**Numerical Advantage Exploitation:**
- "Red's jungler just died bot side. Blue's top laner has TP. Should Blue force a 5v4 fight at dragon?"

**Zone Control:**
- "Blue controls top-side jungle with vision. Baron spawns in 1 minute. How should Red approach setting up for Baron contest?"

**Flank Paths:**
- "Blue wants to engage on Red at dragon. Their assassin can flank from jungle. How does this change the fight geometry?"

### Evaluation Criteria

A high-quality spatial reasoning response should:
1. ✅ **Reference map positions explicitly** (top/bot, jungle quadrants)
2. ✅ **Calculate numerical advantages** (5v4, 3v2, etc.)
3. ✅ **Estimate rotation timings** ("takes 15 seconds to walk from...")
4. ✅ **Consider vision state** (what each team can see)
5. ✅ **Evaluate positional leverage** (how position creates advantage)
6. ✅ **Account for terrain** (walls, choke points, river)

**Red flags:**
- ❌ Ignoring where champions are on the map
- ❌ Not counting numbers in a fight (5v4, etc.)
- ❌ Assuming instant rotations (ignoring travel time)
- ❌ Not considering vision availability

---

## 5. Resource Logic

### Definition
The ability to understand economic principles, evaluate resource trades, calculate gold efficiency, and reason about power spikes, scaling, and resource allocation.

### Cognitive Skills Tested
- **Gold economy understanding**: Knowing objective values, kill bounties, tower gold
- **Resource trade evaluation**: Assessing if a trade was worth (gold, tempo, map control)
- **Power spike recognition**: Understanding champion/item power curves
- **Scaling awareness**: Knowing which teams/champions get stronger over time
- **Opportunity cost reasoning**: Understanding what you give up by choosing option A over B

### Economic Concepts

**Gold Sources:**
- Minions: ~20g per minion, 6 minions/wave = ~120g/wave
- Jungle camps: 50-100g per camp
- Kills: 300g + bounty (0-1000g)
- Towers: 150g global + 250g first tower + plates (160g each)
- Dragons: 25g + permanent buff
- Baron: 300g + 60s buff

**Objective Values:**
- First Tower: 400g total (150g global + 250g killer)
- Dragon Soul: Game-changing permanent buff
- Baron Nashor: ~1500g worth of stats + siege power
- Elder Dragon: Basically wins the game

**Power Spikes:**
- Level spikes: 6, 11, 16 (ultimate upgrades)
- Item spikes: 1st item, 2-item, 3-item
- Scaling: Early game vs. late game champions

**Tempo vs. Value:**
- Trading tower for dragon (give map pressure for permanent buff)
- Dying for a kill (worth if you're a support killing their carry)

### Example Scenarios

**Objective Trade Evaluation:**
- "Blue took dragon while Red took two towers. Who got the better trade?"

**Gold Efficiency:**
- "Red won a teamfight, got 3 kills (900g) and Baron (1500g buff). Blue took an inhibitor (50g). Did Blue's trade make sense?"

**Power Spike Timing:**
- "Blue's ADC just completed their 2nd item at 18 minutes. Should Blue force fights now or wait?"

**Scaling Decisions:**
- "Blue has a late-game scaling comp but is 2k gold down at 20 minutes. Should they force fights or farm?"

**Opportunity Cost:**
- "Blue can contest dragon (50% win chance) or get a free top tower (100% success). Which is better?"

### Evaluation Criteria

A high-quality resource logic response should:
1. ✅ **Quantify gold values** (approximate gold worth of objectives)
2. ✅ **Compare trades numerically** (X gold vs. Y gold)
3. ✅ **Consider non-gold resources** (tempo, map control, vision)
4. ✅ **Reference power spikes** (item/level timings)
5. ✅ **Account for scaling** (early vs. late game advantage)
6. ✅ **Calculate opportunity costs** (what you give up)

**Red flags:**
- ❌ Treating all objectives as equal value
- ❌ Ignoring power spike timings
- ❌ Not considering scaling (treating minute 10 same as minute 30)
- ❌ Valuing kills over objectives (3 kills < 1 Baron usually)

---

## Cross-Cutting Themes

### Theme 1: Game State Awareness
All reasoning types require understanding current game state:
- Gold differential
- Level advantages
- Item completions
- Ultimate availability
- Vision control
- Objective timers

### Theme 2: Risk-Reward Assessment
Every reasoning type involves evaluating risks vs. rewards:
- Probability of success
- Consequences of failure
- Value if successful
- Opportunity cost

### Theme 3: Information Constraints
Strong reasoning acknowledges what information is/isn't available:
- What can be seen with current vision
- What can be inferred from minimap
- What must be guessed/predicted

---

## Integration Across Reasoning Types

Strong strategic understanding often requires **multiple reasoning types simultaneously**:

**Example: Baron Call Decision**
- **Strategic Planning**: Should we start Baron? (multi-option evaluation)
- **Spatial Reasoning**: Where are enemies? Can they contest? (map positioning)
- **Resource Logic**: Is our gold lead large enough? (economy)
- **Causal Inference**: If we get Baron, how does that lead to victory? (forward causation)
- **Error Diagnosis**: What mistakes would we be making if we start now? (risk identification)

This is why **single-factor reasoning** is weak, and **multi-factor integration** is the hallmark of genuine strategic understanding.

---

## Usage in Benchmark

This taxonomy guides:
1. **Task Generation**: Each task targets one primary reasoning type
2. **Reasoning Elements**: Expected reasoning components for LLM-as-judge
3. **Ground Truth Constraints**: Deterministic rules derived from strategic principles
4. **Evaluation**: Separate scoring for each reasoning type enables brittleness analysis (RQ1)

**Research Question Alignment:**
- **RQ1 (Brittleness)**: Compare performance across these 5 types
- **RQ3 (Phase Variance)**: Measure each type across early/mid/late game

---

## References & Sources

This taxonomy is derived from:
- Competitive League of Legends strategic analysis (Worlds, LCS, LCK)
- High-elo gameplay principles (Diamond+, Master, Challenger)
- Strategic coaching resources (LS, Coach Curtis, Neace)
- Game design documentation (Riot Games balance philosophy)

**Note:** Strategic principles evolve with patches. This taxonomy is based on Season 14 meta (Patch 14.x) but core reasoning types are patch-agnostic.