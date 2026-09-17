from openai import OpenAI
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel
from .model_interface import LLMInterface


class OpenAIModel(LLMInterface):
    """
    Interface for OpenAI models via the OpenAI SDK.
    Intended primarily as the LLM-as-judge via generate_raw().
    """

    # Pricing per 1k tokens (USD)
    COST_TABLE = {
        "gpt-4o":      {"input_cost_per_1k": 0.0025,  "output_cost_per_1k": 0.010},
        "gpt-4o-mini": {"input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006},
        "gpt-4-turbo": {"input_cost_per_1k": 0.01,    "output_cost_per_1k": 0.03},
        "o4-mini":     {"input_cost_per_1k": 0.0011,  "output_cost_per_1k": 0.0044},
    }

    # o-series models require temperature=1 and use max_completion_tokens
    _O_SERIES_PREFIXES = ("o1", "o3", "o4")

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        if api_key is None:
            from config import OPENAI_API_KEY
            api_key = OPENAI_API_KEY

        if not api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY in your .env file."
            )

        self._is_o_series = any(model_name.startswith(p) for p in self._O_SERIES_PREFIXES)
        self.model_name = model_name
        # o-series only accepts temperature=1
        self.temperature = 1.0 if self._is_o_series else temperature
        self._client = OpenAI(api_key=api_key)

    def generate_response(self, task: "ReasoningTask", max_tokens: int = 2048) -> str:
        """
        Generate response for a reasoning task with LoL analyst system prompt.

        Args:
            task: ReasoningTask with prompt and context
            max_tokens: Maximum response length

        Returns:
            Model's response as string
        """
        full_prompt = self._construct_prompt(task)
        # o-series models share max_completion_tokens between internal reasoning and
        # visible output. 2048 is often consumed entirely by reasoning, leaving an
        # empty response. Use 16000 so there is always room for a real answer.
        effective_max = 16000 if self._is_o_series else max_tokens
        return self.generate_raw(full_prompt, max_tokens=effective_max)

    def generate_raw(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Send prompt directly to the model without any system prompt wrapping.
        Used by LLMJudge to send judge evaluation prompts as-is.

        Args:
            prompt: Raw prompt string
            max_tokens: Maximum response length

        Returns:
            Model's response as string
        """
        try:
            kwargs: Dict[str, Any] = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
            }
            if self._is_o_series:
                kwargs["max_completion_tokens"] = max_tokens
                kwargs["reasoning_effort"] = "medium"
            else:
                kwargs["temperature"] = self.temperature
                kwargs["max_tokens"] = max_tokens

            response = self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return f"ERROR: {str(e)}"

    def generate_structured(self, prompt: str, response_model: Type[BaseModel], max_tokens: int = 200) -> BaseModel:
        """
        Send prompt and return a structured response parsed into a Pydantic model.
        Used by LLMJudge to guarantee consistent score format.

        Args:
            prompt: Raw prompt string
            response_model: Pydantic model class defining the expected response schema
            max_tokens: Maximum response length

        Returns:
            Parsed Pydantic model instance
        """
        response = self._client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format=response_model,
            max_tokens=max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.parsed

    def _construct_prompt(self, task: "ReasoningTask") -> str:
        """Construct full prompt with match state context."""
        return f"""You are an expert League of Legends analyst. Your analysis must be grounded strictly in the match state provided below. Do not assume, infer, or introduce any information that is not explicitly present in the match state. If the match state does not contain enough information to answer a part of the question, acknowledge that limitation instead of speculating.

MATCH STATE:
{task.compressed_match_state}

QUESTION:
{task.prompt}

Provide a strategic analysis addressing the question using only the information in the match state above."""

    def get_model_name(self) -> str:
        """Return model identifier."""
        return f"openai-{self.model_name}"

    def get_cost_per_token(self) -> Dict[str, float]:
        """Return cost per token for input and output."""
        return self.COST_TABLE.get(
            self.model_name,
            {"input_cost_per_1k": 0.0, "output_cost_per_1k": 0.0},
        )

    def test_connection(self) -> bool:
        """Test if the OpenAI API is reachable and the model is available."""
        try:
            kwargs: Dict[str, Any] = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "Say ok."}],
            }
            if self._is_o_series:
                kwargs["max_completion_tokens"] = 20
            else:
                kwargs["max_tokens"] = 5
            response = self._client.chat.completions.create(**kwargs)
            return len(response.choices) > 0
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
