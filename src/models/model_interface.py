from abc import ABC, abstractmethod
from typing import Dict, Any


class LLMInterface(ABC):
    """Abstract base class for LLM model interfaces."""

    @abstractmethod
    def generate_response(self, task: Any, max_tokens: int = 1000) -> str:
        """Generate response for a reasoning task."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return model identifier."""
        pass

    @abstractmethod
    def get_cost_per_token(self) -> Dict[str, float]:
        """Return cost per token for input and output."""
        pass
