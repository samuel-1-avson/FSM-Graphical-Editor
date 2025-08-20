# fsm_designer_project/ui/ai/ai_providers/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class AIProvider(ABC):
    """
    Abstract Base Class for all AI model providers.

    This class defines the interface that the FSM Designer application uses
    to interact with different AI services (like Gemini, OpenAI, etc.). To add
    a new provider, create a new class that inherits from this one and
    implement all abstract methods.
    """

    @abstractmethod
    def get_name(self) -> str:
        """
        Return the user-friendly name of the provider. This name will be
        displayed in the UI, for example, 'Gemini (Google AI)' or 'OpenAI (GPT)'.
        
        Returns:
            The display name of the AI provider.
        """
        pass

    @abstractmethod
    def configure(self, api_key: str) -> bool:
        """
        Configure the provider with the necessary API key and initialize its client.
        This method should perform a lightweight check to validate the key if possible.
        
        Args:
            api_key: The API key provided by the user.

        Returns:
            True if the configuration was successful and the provider is ready to use,
            False otherwise.

        Raises:
            PermissionError: If the API key is definitively invalid or unauthorized.
            ConnectionRefusedError: If the provider's service cannot be reached due to
                                    network or configuration issues.
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider has been successfully configured with a valid API key.

        Returns:
            True if the provider is ready to generate responses, False otherwise.
        """
        pass

    @abstractmethod
    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        """
        Generate a response from the AI model based on the conversation history.

        Args:
            conversation_history: A list of dictionaries representing the conversation,
                                  following the format:
                                  `[{"role": "user/assistant/system", "content": "..."}]`
            is_json_mode: A hint to request a JSON object as output. The provider should
                          use its specific mechanism to enforce this if available.

        Returns:
            The text response from the model as a string.

        Raises:
            PermissionError: For authentication issues during the API call.
            ConnectionAbortedError: For rate limit errors from the API.
            ConnectionRefusedError: For other connection-related issues.
            Exception: For any other unexpected errors from the provider's library.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Return a dictionary of the provider's supported features. This allows
        the UI to dynamically enable or disable features based on the selected
        AI model.

        Returns:
            A dictionary with boolean flags for supported capabilities.
            Example:
                {
                    "json_mode": True,  # Model supports a dedicated JSON output mode.
                    "tool_use": False,  # Model supports tool/function calling.
                    "streaming": True   # Model supports streaming responses.
                }
        """
        pass