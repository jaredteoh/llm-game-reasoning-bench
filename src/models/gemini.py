import google.generativeai as genai
from typing import Dict, Any, Optional
from .model_interface import LLMInterface


class GeminiModel(LLMInterface):
    """
    Interface for Google Gemini models via the Generative AI SDK.
    """

    # Pricing per 1k tokens (USD)
    COST_TABLE = {
        "models/gemini-2.5-flash": {"input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006},
        "gemini-2.0-flash": {"input_cost_per_1k": 0.000075, "output_cost_per_1k": 0.0003},
        "gemini-2.0-flash-lite": {"input_cost_per_1k": 0.000019, "output_cost_per_1k": 0.000075},
        "gemini-1.5-flash": {"input_cost_per_1k": 0.000075, "output_cost_per_1k": 0.0003},
        "gemini-1.5-pro": {"input_cost_per_1k": 0.00125, "output_cost_per_1k": 0.005},
    }

    def __init__(
        self,
        model_name: str = "models/gemini-2.5-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        """
        Args:
            model_name: Gemini model identifier (e.g., "gemini-2.0-flash")
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

        self.model_name = model_name
        self.temperature = temperature

        genai.configure(api_key=api_key)
        self._client = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
            ),
        )

    def generate_response(self, task: "ReasoningTask", max_tokens: int = 8192) -> str:
        """
        Generate response for a reasoning task.

        Args:
            task: ReasoningTask with prompt and context
            max_tokens: Maximum response length

        Returns:
            Model's response as string
        """
        full_prompt = self._construct_prompt(task)

        try:
            response = self._client.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=self.temperature,
                ),
            )
            # Use candidates path to avoid SDK Part iteration bug with response.text
            return response.candidates[0].content.parts[0].text.strip()

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return f"ERROR: {str(e)}"

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
        return f"gemini-{self.model_name}"

    def get_cost_per_token(self) -> Dict[str, float]:
        """Return cost per token for input and output."""
        return self.COST_TABLE.get(
            self.model_name,
            {"input_cost_per_1k": 0.0, "output_cost_per_1k": 0.0},
        )

    def test_connection(self) -> bool:
        """Test if the Gemini API is reachable and the model is available."""
        try:
            response = self._client.generate_content(
                "Say ok.",
                generation_config=genai.types.GenerationConfig(max_output_tokens=5),
            )
            # Access candidates directly to avoid SDK Part iteration quirks
            return len(response.candidates) > 0
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
