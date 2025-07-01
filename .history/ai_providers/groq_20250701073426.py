# bsm_designer_project/ai_providers/groq.py
import logging
from typing import List, Dict

try:
    import groq
except ImportError:
    groq = None

from .base import AIProvider

logger = logging.getLogger(__name__)

class GroqProvider(AIProvider):
    """AI Provider for models on Groq (e.g., Llama3), using OpenAI-compatible API."""
    def __init__(self, model_name="llama3-70b-8192"):
        if groq is None:
            raise ImportError("The 'groq' library is not installed. Please `pip install groq`.")
        self.model_name = model_name
        self.client: groq.Groq | None = None

    def get_name(self) -> str:
        return "Groq (Llama3)"

    def configure(self, api_key: str) -> bool:
        if not api_key:
            self.client = None
            return False
        try:
            self.client = groq.Groq(api_key=api_key)
            # Groq client doesn't have a lightweight check, assume valid if initialized
            logger.info("GroqProvider configured successfully.")
            return True
        except Exception as e:
            self.client = None
            logger.error(f"Failed to configure GroqProvider: {e}", exc_info=True)
            raise ConnectionRefusedError(f"Failed to initialize Groq client: {e}")

    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        if not self.is_configured():
            raise PermissionError("Groq provider is not configured.")
        
        request_params = {
            "model": self.model_name,
            "messages": conversation_history,
            "temperature": 0.7,
        }
        if is_json_mode:
            request_params["response_format"] = {"type": "json_object"}
            logger.info("GroqProvider: Requesting JSON format.")

        try:
            completion = self.client.chat.completions.create(**request_params)
            response_content = completion.choices[0].message.content
            return response_content or ""
        except groq.AuthenticationError as e:
            raise PermissionError(f"Groq Authentication Error: {e}")
        except groq.RateLimitError as e:
            raise ConnectionAbortedError(f"Groq Rate Limit Exceeded: {e}")
        except Exception as e:
            logger.error(f"GroqProvider.generate_response error: {e}", exc_info=True)
            raise