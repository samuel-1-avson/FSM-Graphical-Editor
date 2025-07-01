# bsm_designer_project/ai_providers/base.py
from abc import ABC, abstractmethod
from typing import List, Dict

class AIProvider(ABC):
    """Abstract Base Class for all AI model providers."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the user-friendly name of the provider (e.g., 'Gemini', 'OpenAI')."""
        pass

    @abstractmethod
    def configure(self, api_key: str) -> bool:
        """
        Configure the provider with the necessary API key.
        Returns True on success, False on failure.
        """
        pass

    @abstractmethod
    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        """
        Generate a response from the AI model.

        Args:
            conversation_history: A list of dictionaries representing the conversation,
                                  following a standard format (e.g., OpenAI's).
            is_json_mode: A hint to request JSON output if the model supports it.

        Returns:
            The text response from the model.
        
        Raises:
            Exception: Should raise specific exceptions for authentication, rate limits, etc.
        """
        pass

    def is_configured(self) -> bool:
        """Returns True if the provider is configured and ready to use."""
        return False