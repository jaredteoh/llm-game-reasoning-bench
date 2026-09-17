"""
Prompt templates for LLM-as-judge evaluation.
Three focused prompts — one per scoring dimension.
"""


def format_reasoning_elements(elements):
    """
    Format reasoning elements for the Relevance judge prompt.

    Args:
        elements: List of ReasoningElement objects/dicts

    Returns:
        Formatted string
    """
    if not elements:
        return "None specified"

    required = []
    expected = []
    for elem in elements:
        importance = elem.get("importance", "expected")
        name = elem.get("name", "Unknown")
        description = elem.get("description", "")
        entry = f"  - {name}: {description}"
        if importance == "required":
            required.append(entry)
        else:
            expected.append(entry)

    lines = []
    if required:
        lines.append("Required (missing these should significantly lower the score):")
        lines.extend(required)
    if expected:
        lines.append("Expected (important but absence should be weighted less heavily):")
        lines.extend(expected)

    return "\n".join(lines)


# --- Relevance prompt ---
# Needs: task prompt + expected reasoning elements + response
RELEVANCE_PROMPT_TEMPLATE = """You are evaluating an LLM's response to a strategic League of Legends question.

QUESTION:
{task_prompt}

EXPECTED REASONING ELEMENTS:
{reasoning_elements}

RESPONSE TO EVALUATE:
{llm_response}

---

Score RELEVANCE on a 1-5 scale.

RELEVANCE measures whether the response addresses the question and covers the expected reasoning elements.

1 = Does not address the question or misses almost all reasoning elements
2 = Partially addresses the question, misses most required elements
3 = Addresses the question adequately, covers some required elements
4 = Fully addresses the question, covers most required elements with minor omissions
5 = Comprehensively addresses all aspects, covers all required and expected elements

Relevance Score (1-5):
Relevance Justification: [1-2 sentences]"""


# --- Coherence prompt ---
# Needs: task prompt + response only
COHERENCE_PROMPT_TEMPLATE = """You are evaluating an LLM's response to a strategic League of Legends question.

QUESTION:
{task_prompt}

RESPONSE TO EVALUATE:
{llm_response}

---

Score COHERENCE on a 1-5 scale.

COHERENCE measures whether the reasoning is internally consistent, logically structured, and well-organised.

1 = Incoherent, contradictory, or illogical
2 = Some logical structure but significant gaps or contradictions
3 = Generally coherent with minor logical issues
4 = Well-structured with sound logic and minimal issues
5 = Perfectly coherent, logically sound, clearly explained

Coherence Score (1-5):
Coherence Justification: [1-2 sentences]"""


# --- Faithfulness prompt ---
# Needs: match state + response only
FAITHFULNESS_PROMPT_TEMPLATE = """You are evaluating an LLM's response to a strategic League of Legends question.

MATCH STATE (Ground Truth):
{match_state}

RESPONSE TO EVALUATE:
{llm_response}

---

Score FAITHFULNESS on a 1-5 scale.

FAITHFULNESS measures whether the response stays grounded in the match state without hallucinating events or facts not present in it.

Check for:
- Correct event references (mentions actual events from match state)
- Accurate facts (gold values, timestamps, objectives are correct)
- No hallucinated events (does not invent things not in the match state)
- Grounded reasoning (bases conclusions on provided evidence)

1 = Multiple hallucinations or major factual errors
2 = Some factual errors or significant ungrounded claims
3 = Mostly accurate with minor inaccuracies
4 = Accurately grounded with very minor issues
5 = Perfectly faithful to match state, all claims verifiable

Faithfulness Score (1-5):
Faithfulness Justification: [1-2 sentences]"""


def construct_relevance_prompt(task, llm_response: str) -> str:
    task_prompt = getattr(task, "prompt", None) or task.get("prompt", "")
    reasoning_elements = getattr(task, "expected_reasoning_elements", None) or task.get(
        "expected_reasoning_elements", []
    )
    return RELEVANCE_PROMPT_TEMPLATE.format(
        task_prompt=task_prompt,
        reasoning_elements=format_reasoning_elements(reasoning_elements),
        llm_response=llm_response,
    )


def construct_coherence_prompt(task, llm_response: str) -> str:
    task_prompt = getattr(task, "prompt", None) or task.get("prompt", "")
    return COHERENCE_PROMPT_TEMPLATE.format(
        task_prompt=task_prompt,
        llm_response=llm_response,
    )


def construct_faithfulness_prompt(task, llm_response: str) -> str:
    match_state = getattr(task, "compressed_match_state", None) or task.get(
        "compressed_match_state", ""
    )
    return FAITHFULNESS_PROMPT_TEMPLATE.format(
        match_state=match_state,
        llm_response=llm_response,
    )


# --- Must-not-recommend violation check prompt ---
# Needs: response + list of must_not_recommend constraints
MUST_NOT_CHECK_TEMPLATE = """You are checking a League of Legends strategy response for critical strategic errors.

GLOBAL RULES — apply these to every constraint before deciding:
1. A VIOLATION requires the response to explicitly recommend or endorse the forbidden content.
   Ask yourself: "Does the response clearly say to DO this, or that this is good/correct?" Only if yes, flag it.
2. NOT a violation — past-event analysis: describing or analysing what already happened is NOT recommending it.
3. NOT a violation — warning or advising against: if the response says the forbidden action is risky,
   inadvisable, or unfavourable, that is the CORRECT answer, not a violation.
4. NOT a violation — acknowledging missing data: noting that information is unavailable is not an endorsement.
5. NOT a violation — negation: if the response calls the forbidden content WRONG, a MISTAKE, an ERROR,
   INCORRECT, or INADVISABLE, that is the OPPOSITE of a violation. Do NOT flag antonyms as violations.
6. "Implies" is not enough — only flag explicit endorsement, not inferred intent.

RESPONSE:
{llm_response}

CONSTRAINTS TO CHECK:
{constraints_block}

Return exactly one result per constraint using the exact constraint_id provided."""


def construct_must_not_prompt(llm_response: str, must_not_constraints: list) -> str:
    blocks = []
    for i, c in enumerate(must_not_constraints, 1):
        forbidden = c["parameters"]["forbidden_recommendations"]
        description = c.get("description", "")
        block_lines = [f"{i}. Constraint ID: {c['constraint_id']}"]
        if description:
            block_lines.append(f"   Context: {description}")
        block_lines.append(
            f"   VIOLATION CONDITION: The response explicitly recommends content equivalent to — "
            f"{'; '.join(forbidden)}"
        )
        block_lines.append(
            f"   NOT a violation if: the response analyses a past event, warns against this action, "
            f"or notes data limitations — or calls the action WRONG, a MISTAKE, or an ERROR."
        )
        blocks.append("\n".join(block_lines))
    constraints_block = "\n\n".join(blocks)
    return MUST_NOT_CHECK_TEMPLATE.format(
        llm_response=llm_response,
        constraints_block=constraints_block,
    )
