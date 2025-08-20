# fsm_designer_project/ui/ai/ai_providers/openai.py
import logging
from typing import List, Dict, Any

try:
    import openai
    import httpx 
except ImportError:
    openai = None
    httpx = None 

from .base import AIProvider

logger = logging.getLogger(__name__)

class OpenAIProvider(AIProvider):
    """AI Provider for OpenAI models (GPT-3.5, GPT-4, etc.)."""
    
    def __init__(self, model_name="gpt-4o"):
        if openai is None or httpx is None: 
            raise ImportError("The 'openai' and 'httpx' libraries are not installed. Please `pip install openai httpx`.")
        self.model_name = model_name
        self.client: openai.OpenAI | None = None

    def get_name(self) -> str:
        """Return the user-friendly name of the provider."""
        return "OpenAI (GPT)"

    def is_configured(self) -> bool:
        """Check if the provider is configured and ready to use."""
        return self.client is not None
        
    def get_capabilities(self) -> Dict[str, Any]:
        """Returns capabilities for modern OpenAI models."""
        return {
            "json_mode": True,  # Supported via response_format={"type": "json_object"}
            "tool_use": True,   # Supported via the 'tools' parameter
            "streaming": True   # Supported for chat completions
        }

    def configure(self, api_key: str) -> bool:
        """
        Configure the OpenAI provider with the API key.
        Performs a lightweight API call to validate the key.
        """
        if not api_key:
            self.client = None
            return False
        try:
            # Use httpx for better connection management, as recommended by OpenAI library
            http_client = httpx.Client()
            self.client = openai.OpenAI(api_key=api_key, http_client=http_client)
            
            # A lightweight check to see if the key is potentially valid by listing models.
            self.client.models.list()
            
            logger.info("OpenAIProvider configured successfully.")
            return True
        except openai.AuthenticationError as e:
            self.client = None
            logger.error(f"OpenAI Authentication Error: {e}")
            raise PermissionError("Invalid OpenAI API key. Please check your key and try again.")
        except Exception as e:
            self.client = None
            logger.error(f"Failed to configure OpenAIProvider: {e}", exc_info=True)
            raise ConnectionRefusedError(f"Failed to connect to OpenAI API: {e}")

    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        """Generate a response from the configured OpenAI model."""
        if not self.is_configured():
            raise PermissionError("OpenAI provider is not configured. Please set a valid API key.")

        request_params = {
            "model": self.model_name,
            "messages": conversation_history,
            "temperature": 0.7,
        }
        
        if is_json_mode and self.get_capabilities()["json_mode"]:
            request_params["response_format"] = {"type": "json_object"}
            logger.info("OpenAIProvider: Requesting JSON format.")

        try:
            completion = self.client.chat.completions.create(**request_params)
            response_content = completion.choices[0].message.content
            return response_content or ""
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI API key is invalid or expired: {e}")
            raise PermissionError(f"OpenAI Authentication Error: {e}")
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            raise ConnectionAbortedError(f"OpenAI Rate Limit Exceeded. Please wait and try again. Details: {e}")
        except openai.APIConnectionError as e:
            logger.error(f"Could not connect to OpenAI API: {e}")
            raise ConnectionRefusedError(f"Could not connect to OpenAI API: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred with the OpenAI provider: {e}", exc_info=True)
            raise