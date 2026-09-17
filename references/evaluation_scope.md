# Evaluation Scope for LoL LLM Benchmark

**Version:** 1.0  
**Last Updated:** February 2026  
**Purpose:** Define clear boundaries for what is and isn't evaluated in the benchmark

---

## Executive Summary

This benchmark evaluates **macro-level strategic reasoning** in League of Legends. It deliberately excludes mechanical execution, micro-positioning, and champion-specific optimizations to focus on high-level decision-making that transfers across patches and champions.

**Core Principle:** We test whether LLMs can **think strategically about complex, multi-agent scenarios**, not whether they've memorized champion matchups or item builds.

---

## 1. In Scope ✅

### 1.1 Macro-Level Strategic Decisions

**What we evaluate:**
- Objective prioritization (Baron vs. Dragon vs. Towers)
- Teamfight engagement timing
- Macro rotations and map movements
- Resource allocation and trading
- Win condition identification

**Why:** These are generalizable reasoning skills that apply across games, patches, and team compositions.

**Example Tasks:**
- "Should Blue team contest this Baron or trade for Bot inhibitor?"
- "Blue is 3k gold ahead at 20 minutes. Should they force fights or farm?"

### 1.2 Causal Understanding

**What we evaluate:**
- Tracing backward from outcomes to causes
- Understanding event cascades (snowball effects)
- Identifying critical turning points in matches
- Explaining why gold leads were gained or lost

**Why:** Causal reasoning is a core cognitive skill that tests genuine understanding vs. pattern matching.

**Example Tasks:**
- "Blue had a 2k gold lead at 15 minutes but was 4k behind at 25 minutes. What caused this 6k swing?"
- "Red lost this teamfight despite having a gold advantage. Why?"

### 1.3 Error Identification

**What we evaluate:**
- Recognizing strategic mistakes
- Explaining why decisions were suboptimal
- Proposing better alternatives
- Assessing error severity (minor vs. game-losing)

**Why:** Error diagnosis tests both domain knowledge and counterfactual reasoning.

**Example Tasks:**
- "Blue started Baron at 30% HP with no vision. What was the mistake?"
- "Identify the critical error that cost Red the game."

### 1.4 Spatial/Positional Reasoning

**What we evaluate:**
- Map control and territorial understanding
- Rotation timing and pathing
- Split push threat assessment
- Numerical advantage exploitation (5v4 scenarios)
- Vision control impact

**Why:** Spatial reasoning tests ability to reason about geometric relationships and positioning.

**Example Tasks:**
- "Blue has 4 members mid, 1 split pushing bot. Red has all 5 mid. What should Red do?"
- "Can Blue's top laner rotate to dragon in time? It spawns in 30 seconds."

### 1.5 Resource Economy

**What we evaluate:**
- Gold value of objectives (towers, dragons, kills)
- Power spike recognition (items, levels)
- Resource trade evaluation (X for Y)
- Scaling awareness (early vs. late game)
- Opportunity cost reasoning

**Why:** Economic reasoning tests understanding of value and trade-offs.

**Example Tasks:**
- "Blue traded 3 kills for a tower and dragon. Who got the better trade?"
- "Rank these options: contest soul dragon, defend mid tower, or take enemy Herald?"

---

## 2. Out of Scope ❌

### 2.1 Mechanical Execution

**What we DON'T evaluate:**
- Last-hitting CS perfectly
- Landing skillshots
- Animation canceling
- Kiting mechanics
- Ability combos (QWER sequences)
- Flash timing precision

**Why excluded:** These are execution skills, not reasoning. An LLM can't "execute" these actions, only reason about higher-level strategy.

**Example of what we DON'T ask:**
- ❌ "How do you execute the Riven fast Q combo?"
- ❌ "What's the optimal AA-cancel pattern for Caitlyn?"

### 2.2 Micro-Positioning in Teamfights

**What we DON'T evaluate:**
- Exact positioning of champions during fights
- Dodging specific skillshots
- Focus targeting order mid-fight
- Auto-spacing (staying at max auto-attack range)

**Why excluded:** This requires frame-by-frame analysis and is too granular for strategic reasoning evaluation.

**What we DO evaluate instead:**
- Whether a teamfight should be engaged at all (macro decision)
- Which objectives to prioritize after winning/losing fight (consequence reasoning)

### 2.3 Champion-Specific Matchups

**What we DON'T evaluate:**
- Detailed lane matchup knowledge (Yasuo vs. Zed)
- Champion-specific power spikes
- Ability interactions (Yasuo windwall blocks what?)
- Counter-pick reasoning

**Why excluded:** Too specific, changes with patches, and doesn't test generalizable reasoning.

**What we DO evaluate instead:**
- Team composition scaling (early vs. late game comps)
- General power spike concepts (level 6, 2-item spikes)

### 2.4 Item Build Optimization

**What we DON'T evaluate:**
- Optimal item build paths
- Situational item choices
- Item efficiency calculations
- Rune selections

**Why excluded:** Build optimization is a narrow domain that changes frequently with patches.

**What we DO evaluate instead:**
- General concept that completed items = power spikes
- Understanding that item advantages translate to combat power

### 2.5 Low-Level Tactical Decisions

**What we DON'T evaluate:**
- When to use Summoner Spells (Flash, Heal) in specific scenarios
- Ward placement exact coordinates
- Jungle clear pathing optimization
- Wave management details (freeze vs. slow push exact mechanics)

**Why excluded:** Too tactical, not strategic. These are important skills but don't test high-level reasoning.

**What we DO evaluate instead:**
- General importance of vision control
- Understanding that Summoner Spells are valuable resources
- Wave state impact on macro rotations

---

## 3. Reasoning Depth Levels

We evaluate reasoning at three depths:

### Level 1: Basic (Single-Factor)
**In Scope:**
- Identifying one key factor
- Making simple comparisons
- Basic causal links

**Example:**
- "Take dragon because it's available" ✓ (minimal but acceptable)

**Out of Scope at this level:**
- Multi-step reasoning
- Complex trade-off evaluation

### Level 2: Intermediate (Multi-Factor)

**In Scope:**
- Considering 2-3 strategic factors
- Weighing trade-offs
- Short causal chains (A → B → C)

**Example:**
- "Take dragon because it's Infernal (high value), we have number advantage (4v3), and enemy jungler is top side" ✓

**Out of Scope at this level:**
- Intricate multi-step plans
- Considering all possible contingencies

### Level 3: Advanced (Strategic Chains)

**In Scope:**
- Multi-step forward planning
- Contingency reasoning
- Long causal chains
- Integration of multiple reasoning types

**Example:**
- "Trade dragon for Herald because we can crash top wave, guarantee Herald, take first tower gold, rotate mid for vision control, set up next dragon at 20 minutes with item advantage" ✓

**Out of Scope:**
- Requires perfect information models didn't have
- Hindsight bias using unknowable information

---

## 4. Temporal Scope

### In Scope: Game Phases

**Early Game (0-14 minutes):**
- Laning decisions
- Early objective priority
- First tower/Herald timing

**Mid Game (14-25 minutes):**
- Teamfight decisions
- Objective trades
- Dragon soul setup

**Late Game (25+ minutes):**
- Baron/Elder priority
- Game-closing plays
- Teamfight engagement with high stakes

**Why this matters:** Reasoning difficulty varies by phase. We test all three.

### Out of Scope: Champion Select

**What we DON'T evaluate:**
- Draft strategy
- Pick/ban reasoning
- Team composition construction

**Why excluded:** Champion select is a separate strategic domain. We focus on in-game reasoning.

---

## 5. Information Constraints

### In Scope: Available Information

**What models have access to:**
- Compressed match state (gold, objectives, timestamps)
- Team compositions
- Game phase (early/mid/late)
- Key events that occurred
- Visible game state at decision point

**What models should reason about:**
- Fog of war (what can/can't be seen)
- Information from previous events in the match
- General game knowledge (how Baron works, etc.)

### Out of Scope: Unknowable Information

**What we DON'T expect models to know:**
- Exact player communication (voice chat)
- Player tilt/mental state
- Technical issues (lag, bugs)
- Off-screen events not in timeline data
- Future events (avoiding hindsight bias)

**Critical:** Tasks must not require information players couldn't have had at decision time.

---

## 6. Evaluation Focus

### What Makes a "Good" Response?

**For Strategic Planning:**
✅ Considers multiple options
✅ Weighs risks vs. rewards
✅ References game state factors
✅ Acknowledges uncertainty
✅ Suggests contingencies

❌ Gives single answer without justification
❌ Ignores obvious risks
❌ Makes absolute claims without caveats

**For Causal Inference:**
✅ Identifies primary cause
✅ Traces causal chain (A → B → C)
✅ Distinguishes correlation from causation
✅ References specific events with timestamps

❌ Attributes outcome to single factor incorrectly
❌ Confuses correlation with causation
❌ Ignores timeline of events

**For Error Diagnosis:**
✅ Identifies the specific error
✅ Explains why it was wrong
✅ Proposes concrete alternative
✅ Assesses severity appropriately

❌ Justifies clearly bad plays
❌ Uses hindsight bias
❌ Doesn't propose alternatives

**For Spatial Reasoning:**
✅ References map positions explicitly
✅ Calculates numerical advantages
✅ Estimates rotation timings
✅ Considers vision state

❌ Ignores where champions are
❌ Doesn't count numbers (5v4)
❌ Assumes instant rotations

**For Resource Logic:**
✅ Quantifies gold values
✅ Compares trades numerically
✅ Considers power spike timing
✅ Accounts for scaling

❌ Treats all objectives as equal
❌ Ignores power spikes
❌ Values kills over objectives blindly

---

## 7. Scoring Philosophy

### Hybrid Evaluation Approach

**Component 1: Rule-Based Constraints (Pass/Fail)**
- Hard requirements (e.g., don't recommend Baron at 10k deficit)
- Objective, deterministic
- Binary: constraint satisfied or violated

**Component 2: LLM-as-Judge (Quality Score)**
- Reasoning depth and completeness
- Consideration of relevant factors
- Clarity of explanation
- Subjective but systematic

**Integration:**
- Must pass rule-based checks to avoid automatic failure
- LLM-as-judge determines quality among valid responses
- Hybrid score = weighted combination

---

## 8. What We're Testing (Meta-Level)

### Cognitive Capabilities

**We ARE testing:**
- Multi-factor reasoning
- Causal understanding
- Strategic planning
- Error recognition
- Spatial reasoning
- Economic reasoning

**We are NOT testing:**
- Factual recall of champion stats
- Memorization of patch notes
- Execution capability
- Real-time decision speed

### Distinguishing Features

**This benchmark differs from typical Q&A benchmarks because:**
1. **Open-ended reasoning** vs. multiple choice trivia
2. **Strategic depth** vs. factual recall
3. **Causal understanding** vs. pattern matching
4. **Context-dependent** vs. universal facts
5. **Hybrid evaluation** vs. exact answer matching

---

## 9. Quality Thresholds

### Minimum Quality for Inclusion

A task must:
✅ Test genuine reasoning (not memorization)
✅ Have clear evaluation criteria
✅ Be based on realistic game scenarios
✅ Have deterministic ground truth constraints
✅ Avoid ambiguity in prompt

A task must NOT:
❌ Require unknowable information
❌ Be answerable without reasoning
❌ Depend on patch-specific knowledge
❌ Test mechanical execution
❌ Have multiple "correct" answers without context

---

## 10. Scope Boundaries Summary

| Category | In Scope ✅ | Out of Scope ❌ |
|----------|------------|----------------|
| **Decision Level** | Macro strategy | Micro mechanics |
| **Reasoning Type** | Multi-factor analysis | Memorized facts |
| **Time Horizon** | Forward planning | Frame-perfect execution |
| **Spatial** | Map-level positioning | Pixel-perfect spacing |
| **Economic** | Objective value trades | Item efficiency math |
| **Knowledge** | General principles | Champion-specific details |
| **Information** | Available game state | Unknowable future/past |
| **Evaluation** | Reasoning quality | Execution skill |

---

## 11. Preventing Scope Creep

### Red Flags for Out-of-Scope Tasks

If a task requires:
- ❌ Specific champion ability knowledge → Too narrow
- ❌ Exact item stats → Too detailed
- ❌ Frame data or animation timing → Too mechanical
- ❌ Information not in match data → Unknowable
- ❌ Patch-specific mechanics → Too volatile

Then it's likely **out of scope**.

### Green Flags for In-Scope Tasks

If a task requires:
- ✅ Comparing multiple strategic options → Good
- ✅ Explaining why something happened → Good
- ✅ Identifying mistakes in macro play → Good
- ✅ Reasoning about map movements → Good
- ✅ Evaluating resource trades → Good

Then it's likely **in scope**.

---

## 12. Alignment with Research Questions

### RQ1: Which reasoning types are most brittle?

**Scope supports:** By clearly defining 5 reasoning types and excluding mechanical skills, we can cleanly compare Strategic Planning vs. Causal Inference vs. Error Diagnosis, etc.

### RQ2: Does hybrid evaluation work better?

**Scope supports:** By defining both rule-based constraints (objective) and reasoning quality criteria (subjective), we enable comparison of evaluation approaches.

### RQ3: How does performance vary by game phase?

**Scope supports:** By defining early/mid/late game scope explicitly, we can measure phase-specific performance.

---

## 13. Evolution and Updates

### When Scope May Expand

**Potential future additions (if time permits):**
- Draft/champion select reasoning
- More granular spatial reasoning (jungle pathings)
- Team coordination reasoning

**Not planned:**
- Mechanical execution will never be in scope
- Patch-specific knowledge will remain out of scope
- Champion-specific optimization will remain out of scope

### Stability Commitment

**Core scope is stable:** The 5 reasoning types and macro-focus will not change during this capstone project to ensure reproducibility and fair comparison.

---

## Usage

This document serves as:
1. **Design Guide**: What tasks to create vs. avoid
2. **Evaluation Reference**: What to score vs. ignore
3. **Thesis Documentation**: Clearly defined scope for academic rigor
4. **Reviewer Transparency**: External stakeholders understand boundaries

Whenever creating a task, ask: **"Does this fit the evaluation scope as defined here?"**

If unsure, err on the side of **broader strategic reasoning** over **narrow technical knowledge**.