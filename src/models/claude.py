import anthropic
from typing import Dict, Any, Optional
from .model_interface import LLMInterface


class ClaudeModel(LLMInterface):
    """
    Interface for Anthropic Claude models via the Anthropic SDK.

    Supports extended thinking via a naming convention: append "-thinking" to
    any model name in the registry (e.g. "claude-sonnet-4-6-thinking").
    """

    # Pricing per 1k tokens (USD)
    COST_TABLE = {
        "claude-haiku-4-5-20251001": {"input_cost_per_1k": 0.001,  "output_cost_per_1k": 0.005},
        "claude-sonnet-4-6":         {"input_cost_per_1k": 0.003,  "output_cost_per_1k": 0.015},
        "claude-opus-4-8":           {"input_cost_per_1k": 0.015,  "output_cost_per_1k": 0.075},
    }

    THINKING_BUDGET_TOKENS = 4096

    def __init__(
        self,
        model_name: str = "claude-sonnet-4-6",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        """
        Args:
            model_name: Claude model identifier. Append "-thinking" for extended
                        thinking mode, e.g. "claude-sonnet-4-6-thinking".
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var via config.
            temperature: Sampling temperature. Forced to 1.0 when thinking is enabled
                         (the API requires this).
        """
        if api_key is None:
            from config import ANTHROPIC_API_KEY
            api_key = ANTHROPIC_API_KEY

        if not api_key:
            raise ValueError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY in your .env file."
            )

        self._thinking_enabled = model_name.endswith("-thinking")
        api_model_name = model_name[: -len("-thinking")] if self._thinking_enabled else model_name

        self.model_name = model_name        # registry name (used for cost lookup)
        self._api_model_name = api_model_name
        # Extended thinking requires temperature == 1.0
        self.temperature = 1.0 if self._thinking_enabled else temperature
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate_response(self, task: "ReasoningTask", max_tokens: int = 8192) -> str:
        full_prompt = self._construct_prompt(task)
        return self.generate_raw(full_prompt, max_tokens=max_tokens)

    def generate_raw(self, prompt: str, max_tokens: int = 1000) -> str:
        try:
            kwargs: Dict[str, Any] = {
                "model": self._api_model_name,
                "max_tokens": max_tokens,
                "temperature": self.temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if self._thinking_enabled:
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": self.THINKING_BUDGET_TOKENS,
                }

            response = self._client.messages.create(**kwargs)

            # Thinking responses include a "thinking" block before the "text" block.
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_blocks).strip()

        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            raise

    def _construct_prompt(self, task: "ReasoningTask") -> str:
        return (
            "You are an expert League of Legends analyst. Your analysis must be grounded "
            "strictly in the match state provided below. Do not assume, infer, or introduce "
            "any information that is not explicitly present in the match state. If the match "
            "state does not contain enough information to answer a part of the question, "
            "acknowledge that limitation instead of speculating.\n\n"
            f"MATCH STATE:\n{task.compressed_match_state}\n\n"
            f"QUESTION:\n{task.prompt}\n\n"
            "Provide a strategic analysis addressing the question using only the information "
            "in the match state above."
        )

    def get_model_name(self) -> str:
        return f"claude-{self.model_name}"

    def get_cost_per_token(self) -> Dict[str, float]:
        return self.COST_TABLE.get(
            self.model_name,
            self.COST_TABLE.get(
                self._api_model_name,
                {"input_cost_per_1k": 0.0, "output_cost_per_1k": 0.0},
            ),
        )

    def test_connection(self) -> bool:
        try:
            response = self._client.messages.create(
                model=self._api_model_name,
                max_tokens=5,
                messages=[{"role": "user", "content": "Say ok."}],
            )
            return len(response.content) > 0
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
