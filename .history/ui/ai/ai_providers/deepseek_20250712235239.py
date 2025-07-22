# fsm_designer_project/ai_providers/deepseek.py
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

class DeepSeekProvider(AIProvider):
    """AI Provider for DeepSeek models, using OpenAI-compatible API."""
    def __init__(self, model_name="deepseek-chat"):
        if openai is None or httpx is None: 
            raise ImportError("The 'openai' and 'httpx' libraries are not installed. Please `pip install openai httpx`.")
        self.model_name = model_name
        self.client: openai.OpenAI | None = None
        self.base_url = "https://api.deepseek.com/v1"

    def get_name(self) -> str:
        return "DeepSeek"

    def is_configured(self) -> bool:
        return self.client is not None

    def configure(self, api_key: str) -> bool:
        if not api_key:
            self.client = None
            return False
        try:
            http_client = httpx.Client()
            self.client = openai.OpenAI(api_key=api_key, base_url=self.base_url, http_client=http_client)
            # --- FIX: Updated API call for connection test ---
            self.client.models.list()
            logger.info("DeepSeekProvider configured successfully.")
            return True
        except openai.AuthenticationError as e:
            self.client = None
            logger.error(f"DeepSeek Authentication Error: {e}")
            raise PermissionError("Invalid DeepSeek API key.")
        except Exception as e:
            self.client = None
            logger.error(f"Failed to configure DeepSeekProvider: {e}", exc_info=True)
            raise ConnectionRefusedError(f"Failed to connect to DeepSeek: {e}")

    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        if not self.is_configured():
            raise PermissionError("DeepSeek provider is not configured.")
        
        request_params = {
            "model": self.model_name,
            "messages": conversation_history,
            "temperature": 0.7,
        }
        # DeepSeek may not support OpenAI's JSON mode syntax, so we instruct it via prompt
        if is_json_mode:
            # Add instruction to the last user message to enforce JSON output
            if conversation_history and conversation_history[-1]['role'] == 'user':
                 conversation_history[-1]['content'] += "\n\nIMPORTANT: Respond with ONLY the valid JSON object requested. Do not include any other text, explanations, or markdown formatting."
        
        try:
            completion = self.client.chat.completions.create(**request_params)
            response_content = completion.choices[0].message.content
            return response_content or ""
        except openai.AuthenticationError as e:
            raise PermissionError(f"DeepSeek Authentication Error: {e}")
        except openai.RateLimitError as e:
            raise ConnectionAbortedError(f"DeepSeek Rate Limit Exceeded: {e}")
        except Exception as e:
            logger.error(f"DeepSeekProvider.generate_response error: {e}", exc_info=True)
            raise