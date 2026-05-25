import requests
import json
from typing import Optional, Dict, Any
from .model_interface import LLMInterface


class OllamaModel(LLMInterface):
    """
    Interface for locally-hosted Ollama models.
    Free to use, good for testing pipeline before using paid APIs.
    """

    def __init__(
        self,
        model_name: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
    ):
        """
        Args:
            model_name: Ollama model identifier (e.g., "llama3.1:8b")
            base_url: Ollama API endpoint
            temperature: Sampling temperature (0.0 = deterministic)
        """
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.api_endpoint = f"{base_url}/api/generate"

    def generate_response(self, task: "ReasoningTask", max_tokens: int = 2048) -> str:
        """
        Generate response for a reasoning task.

        Args:
            task: ReasoningTask with prompt and context
            max_tokens: Maximum response length

        Returns:
            Model's response as string
        """
        # Construct full prompt with context
        full_prompt = self._construct_prompt(task)

        # Call Ollama API
        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": max_tokens},
        }

        try:
            response = requests.post(
                self.api_endpoint, json=payload, timeout=120  # 2 minute timeout
            )
            response.raise_for_status()

            result = response.json()
            return result["response"].strip()

        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
            return f"ERROR: {str(e)}"

    def _construct_prompt(self, task: "ReasoningTask") -> str:
        """
        Construct full prompt with match state context.

        Args:
            task: ReasoningTask object

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert League of Legends analyst. Your analysis must be grounded strictly in the match state provided below. Do not assume, infer, or introduce any information that is not explicitly present in the match state. If the match state does not contain enough information to answer a part of the question, acknowledge that limitation instead of speculating.

MATCH STATE:
{task.compressed_match_state}

QUESTION:
{task.prompt}

Provide a strategic analysis addressing the question using only the information in the match state above."""

        return prompt

    def get_model_name(self) -> str:
        """Return model identifier."""
        return f"ollama-{self.model_name}"

    def get_cost_per_token(self) -> Dict[str, float]:
        """Ollama is free - return 0 costs."""
        return {"input_cost_per_1k": 0.0, "output_cost_per_1k": 0.0}

    def test_connection(self) -> bool:
        """
        Test if Ollama is running and model is available.

        Returns:
            True if connection successful
        """
        try:
            # Test with simple prompt
            payload = {
                "model": self.model_name,
                "prompt": "Test",
                "stream": False,
                "options": {"num_predict": 10},
            }
            response = requests.post(self.api_endpoint, json=payload, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Initialize model
    model = OllamaModel(model_name="llama3.1:8b")

    # Test connection
    print("Testing Ollama connection...")
    if model.test_connection():
        print("Connection successful")
    else:
        print("Connection failed. Is Ollama running?")
        print("Start Ollama with: ollama serve")
        exit(1)

    # Test with sample task
    from dataclasses import dataclass

    @dataclass
    class SampleTask:
        compressed_match_state: str
        prompt: str

    sample = SampleTask(
        compressed_match_state="""
=== MATCH STATE (24:00) ===
Gold: Blue 78,234 | Red 75,956 | Diff: +2,278 (Blue ahead)
Baron: Available
Vision: Blue has 3 wards around Baron pit
Status: All 10 champions alive
""",
        prompt="Blue team has a 2,278 gold lead at 24 minutes and vision control around Baron pit. Should they start Baron immediately? Explain your strategic reasoning.",
    )

    print("\nGenerating response...")
    response = model.generate_response(sample)
    print(f"\nModel response:\n{response}")
