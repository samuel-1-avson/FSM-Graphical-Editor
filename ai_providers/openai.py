# fsm_designer_project/ai_providers/openai.py
import logging
from typing import List, Dict

try:
    import openai
    import httpx 
except ImportError:
    openai = None
    httpx = None 

from .base import AIProvider

logger = logging.getLogger(__name__)

class OpenAIProvider(AIProvider):
    """AI Provider for OpenAI models (GPT-3.5, GPT-4)."""
    def __init__(self, model_name="gpt-4o"):
        if openai is None or httpx is None: 
            raise ImportError("The 'openai' and 'httpx' libraries are not installed. Please `pip install openai httpx`.")
        self.model_name = model_name
        self.client: openai.OpenAI | None = None

    def get_name(self) -> str:
        return "OpenAI (GPT)"

    def is_configured(self) -> bool:
        return self.client is not None

    def configure(self, api_key: str) -> bool:
        if not api_key:
            self.client = None
            return False
        try:
            http_client = httpx.Client()
            self.client = openai.OpenAI(api_key=api_key, http_client=http_client)
            # --- FIX: Updated API call for connection test ---
            # A lightweight check to see if the key is potentially valid
            # Simply iterating to get the first item is a lightweight way to test.
            self.client.models.list()
            logger.info("OpenAIProvider configured successfully.")
            return True
        except openai.AuthenticationError as e:
            self.client = None
            logger.error(f"OpenAI Authentication Error: {e}")
            raise PermissionError("Invalid OpenAI API key.")
        except Exception as e:
            self.client = None
            logger.error(f"Failed to configure OpenAIProvider: {e}", exc_info=True)
            raise ConnectionRefusedError(f"Failed to connect to OpenAI: {e}")

    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        if not self.is_configured():
            raise PermissionError("OpenAI provider is not configured.")

        request_params = {
            "model": self.model_name,
            "messages": conversation_history,
            "temperature": 0.7,
        }
        if is_json_mode:
            request_params["response_format"] = {"type": "json_object"}
            logger.info("OpenAIProvider: Requesting JSON format.")

        try:
            completion = self.client.chat.completions.create(**request_params)
            response_content = completion.choices[0].message.content
            return response_content or ""
        except openai.AuthenticationError as e:
            raise PermissionError(f"OpenAI Authentication Error: {e}")
        except openai.RateLimitError as e:
            raise ConnectionAbortedError(f"DeepSeek Rate Limit Exceeded: {e}")
        except Exception as e:
            logger.error(f"OpenAIProvider.generate_response error: {e}", exc_info=True)
            raise