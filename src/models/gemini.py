from google import genai
from google.genai import types
from typing import Dict, Any, Optional
from .model_interface import LLMInterface


def _is_gemini3(model_name: str) -> bool:
    """True for Gemini 3.x models, which use thinkingLevel instead of thinkingBudget."""
    base = model_name.lstrip("models/")
    return base.startswith("gemini-3")


class GeminiModel(LLMInterface):
    """
    Interface for Google Gemini models via the google-genai SDK.

    Supports thinking/reasoning mode via a naming convention: append "-thinking"
    to any model name in the registry (e.g. "gemini-3.5-flash-thinking").
    2.5-series models use thinkingBudget=8192; 3.x-series use thinkingLevel="medium".
    """

    # Pricing per 1k tokens (USD) — updated June 2026
    COST_TABLE = {
        # 2.5 series
        "models/gemini-2.5-pro":            {"input_cost_per_1k": 0.00125,  "output_cost_per_1k": 0.010},
        "models/gemini-2.5-flash":           {"input_cost_per_1k": 0.0003,   "output_cost_per_1k": 0.0025},
        "gemini-2.5-flash":                  {"input_cost_per_1k": 0.0003,   "output_cost_per_1k": 0.0025},
        "gemini-2.5-flash-lite":             {"input_cost_per_1k": 0.0001,   "output_cost_per_1k": 0.0004},
        "models/gemini-2.5-flash-lite":      {"input_cost_per_1k": 0.0001,   "output_cost_per_1k": 0.0004},
        # 3.x series
        "gemini-3.5-flash":                  {"input_cost_per_1k": 0.0015,   "output_cost_per_1k": 0.009},
        "gemini-3-flash-preview":            {"input_cost_per_1k": 0.0005,   "output_cost_per_1k": 0.003},
        "gemini-3.1-flash-lite":             {"input_cost_per_1k": 0.00025,  "output_cost_per_1k": 0.0015},
        "gemini-3.1-pro-preview":            {"input_cost_per_1k": 0.002,    "output_cost_per_1k": 0.012},
    }

    def __init__(
        self,
        model_name: str = "models/gemini-2.5-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        """
        Args:
            model_name: Gemini model identifier. Append "-thinking" for thinking mode,
                        e.g. "gemini-3.5-flash-thinking" or "gemini-2.5-flash-thinking".
            api_key: Google AI API key. Falls back to GEMINI_API_KEY env var via config.
            temperature: Sampling temperature (0.0 = deterministic)
        """
        if api_key is None:
            from config import GEMINI_API_KEY
            api_key = GEMINI_API_KEY

        if not api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY in your .env file."
            )

        # Detect and strip the "-thinking" registry suffix
        self._thinking_config: Optional[types.ThinkingConfig] = None
        api_model_name = model_name
        if model_name.endswith("-thinking"):
            api_model_name = model_name[: -len("-thinking")]
            if _is_gemini3(api_model_name):
                self._thinking_config = types.ThinkingConfig(thinking_level="medium")
            else:
                self._thinking_config = types.ThinkingConfig(thinking_budget=8192)

        self.model_name = model_name        # registry name (used for cost lookup)
        self._api_model_name = api_model_name
        self.temperature = temperature
        self._client = genai.Client(api_key=api_key)

    def generate_response(self, task: "ReasoningTask", max_tokens: int = 8192) -> str:
        full_prompt = self._construct_prompt(task)

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=self.temperature,
            thinking_config=self._thinking_config,
        )

        try:
            response = self._client.models.generate_content(
                model=self._api_model_name,
                contents=full_prompt,
                config=config,
            )

            # Thinking models return multiple parts; skip thought parts, keep text.
            parts = response.candidates[0].content.parts
            text_parts = [
                p.text for p in parts
                if hasattr(p, "text") and p.text and not getattr(p, "thought", False)
            ]
            return ("\n".join(text_parts) if text_parts else parts[0].text).strip()

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
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
        return f"gemini-{self.model_name}"

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
            response = self._client.models.generate_content(
                model=self._api_model_name,
                contents="Say ok.",
                config=types.GenerateContentConfig(max_output_tokens=5),
            )
            return len(response.candidates) > 0
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
