# fsm_designer_project/ai_providers/groq.py
import logging
from typing import List, Dict

try:
    import openai # Groq uses an OpenAI-compatible client
    import httpx
except ImportError:
    openai = None
    httpx = None

from .base import AIProvider

logger = logging.getLogger(__name__)

class GroqProvider(AIProvider):
    """AI Provider for Groq models (Llama3, etc.), using an OpenAI-compatible API."""
    def __init__(self, model_name="llama3-70b-8192"):
        if openai is None or httpx is None:
            raise ImportError("The 'openai' and 'httpx' libraries are not installed. Please `pip install openai httpx`.")
        self.model_name = model_name
        self.client: openai.OpenAI | None = None
        self.base_url = "https://api.groq.com/openai/v1"

    def get_name(self) -> str:
        return "Groq (Llama3)"

    def is_configured(self) -> bool:
        return self.client is not None

    def configure(self, api_key: str) -> bool:
        if not api_key:
            self.client = None
            return False
        try:
            http_client = httpx.Client()
            self.client = openai.OpenAI(api_key=api_key, base_url=self.base_url, http_client=http_client)
            # A lightweight check to see if the key is potentially valid
            self.client.models.list()
            logger.info("GroqProvider configured successfully.")
            return True
        except openai.AuthenticationError as e:
            self.client = None
            logger.error(f"Groq Authentication Error: {e}")
            raise PermissionError("Invalid Groq API key.")
        except Exception as e:
            self.client = None
            logger.error(f"Failed to configure GroqProvider: {e}", exc_info=True)
            raise ConnectionRefusedError(f"Failed to connect to Groq: {e}")

    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        if not self.is_configured():
            raise PermissionError("Groq provider is not configured.")
        
        request_params = {
            "model": self.model_name,
            "messages": conversation_history,
            "temperature": 0.7,
        }
        # Groq doesn't officially support the json_object response format.
        # We must instruct it via the system prompt (which is handled in ChatbotWorker).
        if is_json_mode:
             # Add instruction to the last user message to enforce JSON output
            if conversation_history and conversation_history[-1]['role'] == 'user':
                 conversation_history[-1]['content'] += "\n\nIMPORTANT: Respond with ONLY the valid JSON object requested. Do not include any other text, explanations, or markdown formatting."

        try:
            completion = self.client.chat.completions.create(**request_params)
            response_content = completion.choices[0].message.content
            return response_content or ""
        except openai.AuthenticationError as e:
            raise PermissionError(f"Groq Authentication Error: {e}")
        except openai.RateLimitError as e:
            raise ConnectionAbortedError(f"Groq Rate Limit Exceeded: {e}")
        except Exception as e:
            logger.error(f"GroqProvider.generate_response error: {e}", exc_info=True)
            raise