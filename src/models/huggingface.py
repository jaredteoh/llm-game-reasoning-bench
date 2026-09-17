from openai import OpenAI
from typing import Dict, Any, Optional
from .model_interface import LLMInterface

HF_BASE_URL = "https://router.huggingface.co/v1"


class HuggingFaceModel(LLMInterface):
    """
    Interface for HuggingFace Inference Providers via the OpenAI-compatible router.

    DeepSeek-R1 (reasoning model) can be selected by appending "-thinking" to the
    registry key. The <think>...</think> reasoning trace is stripped; only the final
    answer is returned.
    """

    COST_TABLE = {
        "deepseek-ai/DeepSeek-V3":       {"input_cost_per_1k": 0.00027, "output_cost_per_1k": 0.00110},
        "deepseek-ai/DeepSeek-R1":       {"input_cost_per_1k": 0.00040, "output_cost_per_1k": 0.00160},
        "deepseek-ai/DeepSeek-R1-0528":  {"input_cost_per_1k": 0.00040, "output_cost_per_1k": 0.00160},
    }

    def __init__(
        self,
        model_name: str = "deepseek-ai/DeepSeek-V3",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        if api_key is None:
            from config import HF_TOKEN
            api_key = HF_TOKEN

        if not api_key:
            raise ValueError(
                "HuggingFace token is required. Set HF_TOKEN in your .env file."
            )

        self._strip_thinking = model_name.endswith("-thinking")
        api_model_name = model_name[: -len("-thinking")] if self._strip_thinking else model_name

        self.model_name = model_name
        self._api_model_name = api_model_name
        self.temperature = temperature
        self._client = OpenAI(api_key=api_key, base_url=HF_BASE_URL)

    def generate_response(self, task: "ReasoningTask", max_tokens: int = 8192) -> str:
        full_prompt = self._construct_prompt(task)
        return self.generate_raw(full_prompt, max_tokens=max_tokens)

    def generate_raw(self, prompt: str, max_tokens: int = 1000) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._api_model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content or ""
            if self._strip_thinking:
                text = _strip_think_tags(text)
            return text.strip()

        except Exception as e:
            print(f"Error calling HuggingFace API: {e}")
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
        return f"huggingface-{self.model_name}"

    def get_cost_per_token(self) -> Dict[str, float]:
        return self.COST_TABLE.get(
            self._api_model_name,
            {"input_cost_per_1k": 0.0, "output_cost_per_1k": 0.0},
        )

    def test_connection(self) -> bool:
        try:
            response = self._client.chat.completions.create(
                model=self._api_model_name,
                messages=[{"role": "user", "content": "Say ok."}],
                max_tokens=5,
            )
            return len(response.choices) > 0
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks emitted by DeepSeek-R1."""
    import re
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
